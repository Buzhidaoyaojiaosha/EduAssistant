from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from app.models.NewAdd import AIQuestion,AiQuestionStudentAnswer
from app.models.learning_data import StudentKnowledgePoint
from app.models.course import Course
from app.utils.llm.deepseek import chat_deepseek
from datetime import datetime

wrongbook_bp = Blueprint('wrongbook', __name__, url_prefix='/wrongbook')
@wrongbook_bp.route('/practice_questions', methods=['GET'])
def practice_questions():
    """显示练习题目，包含学生已作答的记录"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    course_id = request.args.get('course_id', type=int)
    original_question_id = request.args.get('question_id', type=int)
    if not course_id:
        return "缺少课程ID参数", 400
    
    # 获取课程信息
    course = Course.get_by_id(course_id)
    if not course:
        return "课程不存在", 404
    
    # 获取题目及学生答题记录
    questions = (AIQuestion
                .select()
                .where((AIQuestion.course == course_id) & 
                       (AIQuestion.is_approved == True)&
                       (AIQuestion.original_question == original_question_id))
                .order_by(AIQuestion.created_time.desc())
                .limit(10))
    
    questions_with_answers = []
    for question in questions:
        # 查询学生是否已经回答过这道题
        answer_record = (AiQuestionStudentAnswer
                        .select()
                        .where(
                            (AiQuestionStudentAnswer.ai_question == question.ai_question_id) &
                            (AiQuestionStudentAnswer.student == session['user_id'])
                        )
                        .order_by(AiQuestionStudentAnswer.submission_time.desc())
                        .first())
        
        questions_with_answers.append({
            'question': question,
            'answer_record': answer_record
        })
    
    return render_template('wrongbook/practice.html', 
                         course=course,
                         questions_with_answers=questions_with_answers)


@wrongbook_bp.route('/ai_check', methods=['POST'])
def ai_check_answer():
    """
    AI纠错接口
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    data = request.get_json()
    question_id = data.get('question_id')
    student_answer = data.get('student_answer')
    
    if not question_id or not student_answer:
        return jsonify({'success': False, 'error': '缺少参数'}), 400
    print(f"调用aicheck")
    try:
        # 获取题目信息
        ai_question = AIQuestion.get_by_id(question_id)
        if not ai_question:
            return jsonify({'success': False, 'error': '题目不存在'}), 404
        print(f"AI Question: {ai_question.context}, Answer: {ai_question.answer}, Student Answer: {student_answer}")
        # 调用DeepSeek API生成反馈
        feedback = generate_ai_feedback(
            question_context=ai_question.context,
            question_answer=ai_question.answer,
            student_answer=student_answer,
            question_type=ai_question.status
        )
        
        # 保存到数据库
        AiQuestionStudentAnswer.create(
            student=session['user_id'],
            ai_question=question_id,
            student_answer=student_answer,
            ai_feedback=feedback,
            submission_time=datetime.now()
        )
        
        return jsonify({
            'success': True,
            'feedback': feedback
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_ai_feedback(question_context, question_answer, student_answer, question_type):
    """
    调用DeepSeek生成纠错反馈
    """
    # 根据题目类型构造不同的提示词
    question_type_map = {
        1: "选择题",
        2: "判断题", 
        3: "简答题"
    }
    
    prompt = f"""
    你是一位经验丰富的教师，正在批改学生作业。请根据以下信息提供详细的纠错反馈：
    
    【题目类型】{question_type_map.get(question_type, '未知类型')}
    【题目内容】{question_context}
    【标准答案】{question_answer}
    【学生答案】{student_answer}
    
    请按照以下要求提供反馈：
    1. 首先判断答案是否正确
    2. 如果错误，分析错误原因
    3. 给出详细的解题思路
    4. 提供相关知识点的复习建议
    5. 语言简洁专业，使用中文
    6. 限制在200字以内
    
    反馈格式：
    【正误判断】...
    【错误分析】...
    【解题思路】...
    【复习建议】...
    """
    
    messages = [
        {"role": "system", "content": "你是一位专业教师，擅长分析学生错误并提供学习建议。"},
        {"role": "user", "content": prompt}
    ]
    
    try:
        # 调用DeepSeek API
        response_text = chat_deepseek(messages)
        return response_text.strip() if response_text else "AI反馈生成失败"
    except Exception as e:
        return f"AI服务暂时不可用: {str(e)}"