from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from app.models.NewAdd import AIQuestion
from app.models.learning_data import StudentKnowledgePoint
from app.models.course import Course

wrongbook_bp = Blueprint('wrongbook', __name__, url_prefix='/wrongbook')

@wrongbook_bp.route('/practice_questions', methods=['GET'])
def practice_questions():
    """
    再练几题页面
    显示AI生成的练习题目
    """
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    course_id = request.args.get('course_id', type=int)
    if not course_id:
        return "缺少课程ID参数", 400
    
    # 获取课程信息
    course = Course.get_by_id(course_id)
    if not course:
        return "课程不存在", 404
    
    # 获取该课程的AI生成题目（已审核通过的）
    questions = (AIQuestion
                .select()
                .where((AIQuestion.course == course_id) & 
                       (AIQuestion.is_approved == True))
                .order_by(AIQuestion.created_time.desc())
                .limit(10))  # 限制10道题
    
    return render_template('wrongbook/practice.html', 
                         course=course,
                         questions=questions) 