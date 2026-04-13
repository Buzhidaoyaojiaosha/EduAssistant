from flask import Blueprint, request, jsonify,current_app
from app.models.assignment import Assignment, StudentAssignment
from app.models.user import User
from app.models.course import Course
from app.models.NewAdd import Question, StudentAnswer, Feedback, WrongBook, QuestionWrongBook
from app.utils.result import Result
import datetime
import os
import uuid
import subprocess
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, current_app

homework_api_bp = Blueprint('homework_api', __name__, url_prefix='/homeworkApi')

@homework_api_bp.route('/homeworks/question', methods=['POST'])
def get_question_detail():
    """获取题目详情"""
    data = request.json
    student_id = data.get('studentId')
    question_id = data.get('questionId')
    
    if not student_id or not question_id:
        return jsonify(Result.error("缺少必要参数", 400)), 400
    
    try:
        # 查询题目
        question = Question.get_or_none(Question.question_id == question_id)
        
        if not question:
            return jsonify(Result.error("题目不存在", 404)), 404
        
        response_data = {
            "questionId": question.question_id,
            "homeworkId": question.assignment_id,
            "questionName": question.question_name,
            "score": question.score,
            "context": question.context,
            "status": question.status,
            "subjectId": question.course_id
        }
        
        return jsonify(Result.success(response_data))
    
    except Exception as e:
        return jsonify(Result.error("查看题目失败", 400)), 400

@homework_api_bp.route('/homeworks', methods=['POST'])
def get_student_homeworks():
    """获取学生的作业列表，可按科目筛选"""
    data = request.json
    student_id = data.get('studentId')
    subject_id = data.get('subject')  # 可选
    
    if not student_id:
        return jsonify(Result.error("缺少必要参数", 400)), 400
    
    try:
        # 查询学生的作业
        query = StudentAssignment.select().where(StudentAssignment.student_id == student_id)
        
        # 如果指定了科目，添加过滤条件
        if subject_id:
            query = query.where(StudentAssignment.course_id == subject_id)
        
        student_assignments = list(query)
        
        if not student_assignments:
            return jsonify(Result.success([])), 200
        
        response_data = []
        for sa in student_assignments:
            response_data.append({
                "homeworkId": sa.assignment_id,
                "subjectId": sa.course_id,
                "status": sa.status,
                "totalScore": sa.total_score,
                "finalScore": sa.final_score,
                "workTime": sa.work_time.strftime("%Y-%m-%d %H:%M:%S") if sa.work_time else None
            })
        
        return jsonify(Result.success(response_data))
    
    except Exception as e:
        return jsonify(Result.error(f"查询错误: {str(e)}", 500)), 500

@homework_api_bp.route('/wrongBooks', methods=['POST'])
def get_wrong_books():
    """获取学生的错题本详情"""
    data = request.json
    student_id = data.get('studentId')
    wrong_book_id = data.get('wrongBookId')
    subject_id = data.get('subjectId')  # 可选
    
    if not student_id or not wrong_book_id:
        return jsonify(Result.error("缺少必要参数", 400)), 400
    
    try:
        # 查询错题本
        wrong_book = WrongBook.get_or_none(WrongBook.wrong_book_id == wrong_book_id, 
                                          WrongBook.student_id == student_id)
        
        if not wrong_book:
            return jsonify(Result.error("错题本不存在", 404)), 404
        
        # 查询错题本中的题目
        query = (QuestionWrongBook
                .select(QuestionWrongBook, Question, StudentAnswer)
                .join(Question)
                .join_from(Question, StudentAnswer, on=(
                    (StudentAnswer.question_id == Question.question_id) & 
                    (StudentAnswer.student_id == student_id)
                ))
                .where(QuestionWrongBook.wrong_book_id == wrong_book_id))
        
        # 如果指定了科目，添加过滤条件
        if subject_id:
            query = query.where(Question.course_id == subject_id)
        
        results = list(query)
        
        if not results:
            return jsonify(Result.success(["无错题记录"])), 404
        
        response_data = []
        for result in results:
            question = result.question
            student_answer = result.question.student_answers[0]  # 假设一个学生对一个题目只有一个答案
            
            response_data.append({
                "questionId": question.question_id,
                "homeworkId": question.assignment_id,
                "questionName": question.question_name,
                "score": question.score,
                "context": question.context,
                "answer": question.answer,
                "analysis": question.analysis,
                "status": question.status,
                "subjectId": question.course_id,
                "submissionId": student_answer.submission_id,
                "studentId": student_answer.student_id,
                "commitAnswer": student_answer.commit_answer,
                "earnedScore": student_answer.earned_score,
                "workTime": student_answer.work_time.strftime("%Y-%m-%d %H:%M:%S") if student_answer.work_time else None
            })
        
        return jsonify(Result.success(response_data))
    
    except Exception as e:
        return jsonify(Result.error(f"查询错误: {str(e)}", 500)), 500

@homework_api_bp.route('/homeworks/feedback', methods=['POST'])
def get_homework_feedback():
    """获取学生所有已批改且有教师反馈的作业列表"""
    data = request.json
    student_id = data.get('studentId')
    
    if not student_id:
        return jsonify(Result.error("缺少必要参数", 400)), 400
    
    try:
        # 查询有反馈的作业
        feedbacks = (Feedback
                    .select(Feedback, Assignment)
                    .join(Assignment)
                    .where(Feedback.student_id == student_id))
        
        if not feedbacks:
            return jsonify(Result.success([])), 200
        
        response_data = []
        for feedback in feedbacks:
            response_data.append({
                "homeworkName": feedback.assignment.title,
                "homeworkId": feedback.assignment_id,
                "comment": feedback.comment
            })
        
        return jsonify(Result.success(response_data))
    
    except Exception as e:
        return jsonify(Result.error(f"查询错误: {str(e)}", 500)), 500

@homework_api_bp.route('/homeworks/questionlist', methods=['POST'])
def get_homework_questions():
    """获取作业包含的题目列表"""
    data = request.json
    homework_id = data.get('homeworkId')
    
    if not homework_id:
        return jsonify(Result.error("缺少必要参数", 400)), 400
    
    try:
        # 查询作业的题目
        questions = Question.select(Question.question_id).where(Question.assignment_id == homework_id)
        
        if not questions:
            return jsonify(Result.success([])), 200
        
        question_ids = [q.question_id for q in questions]
        
        return jsonify({
            "code": 200,
            "message": "success",
            "data": question_ids
        })
    
    except Exception as e:
        return jsonify(Result.error(f"查询错误: {str(e)}", 500)), 500



@homework_api_bp.route('/homeworks/submit', methods=['POST'])
def submit_homework_answer():
    """学生提交题目答案（支持文件上传）"""
    # 获取请求参数
    student_id = request.form.get('studentId')
    question_id = request.form.get('questionId')
    select_answer = request.form.get('selectAnswer')  # 选择题或判断题答案
    
    # 检查必填参数
    if not student_id or not question_id:
        return jsonify(Result.error("缺少必要参数", 400)), 400
    
    try:
        # 查询题目信息
        question = Question.get_or_none(Question.question_id == question_id)
        if not question:
            return jsonify(Result.error("题目不存在", 404)), 404
        
        # 查询学生信息
        student = User.get_or_none(User.id == student_id)
        if not student:
            return jsonify(Result.error("学生不存在", 404)), 404
        
        # 获取当前时间
        current_time = datetime.now()
        
        # 处理选择题或判断题答案
        if select_answer:
            # 创建或更新学生答案
            student_answer, created = StudentAnswer.get_or_create(
                student_id=student_id,
                question_id=question_id,
                defaults={
                    'commit_answer': select_answer,
                    'earned_score': 0,  # 初始得分为0，等待教师批改
                    'work_time': current_time,
                    'answerImagePath': None  # 选择题没有图片
                }
            )
            
            if not created:
                # 如果记录已存在，更新答案和时间
                student_answer.commit_answer = select_answer
                student_answer.work_time = current_time
                student_answer.save()
            
            # 更新学生作业状态和时间
            update_student_assignment(student_id, question.assignment_id, current_time)
            
            return jsonify(Result.success({
                "submissionId": student_answer.submission_id,
                "status": "已提交",
                "workTime": current_time.strftime("%Y-%m-%d %H:%M:%S")
            }))
        
        # 处理文件上传（客观题）
        elif 'file' in request.files:
            file = request.files['file']
            
            # 检查文件是否存在
            if file.filename == '':
                return jsonify(Result.error("未选择文件", 400)), 400
            
            # 检查文件类型
            allowed_extensions = {'jpg', 'jpeg', 'png', 'pdf', 'docx'}
            file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            
            if file_ext not in allowed_extensions:
                return jsonify(Result.error("不支持的文件类型", 400)), 400
            
            # 创建上传目录
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'homework_answers')
            os.makedirs(upload_dir, exist_ok=True)
            
            # 生成唯一文件名
            filename = secure_filename(f"{student_id}_{question_id}_{uuid.uuid4()}.{file_ext}")
            file_path = os.path.join(upload_dir, filename)
            
            # 保存文件
            file.save(file_path)
            
            # 如果是图片文件，进行OCR处理
            answer_text = ""
            answer_image_path = None
            
            if file_ext in {'jpg', 'jpeg', 'png'}:
                # 创建OCR结果目录
                ocr_result_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'ocr_results')
                os.makedirs(ocr_result_dir, exist_ok=True)
                
                # 创建答案图片目录
                answer_images_dir = os.path.join(ocr_result_dir, 'answer_images')
                os.makedirs(answer_images_dir, exist_ok=True)
                
                # 生成OCR结果文件路径
                timestamp = str(int(datetime.now().timestamp()))
                ocr_output_file = os.path.join(ocr_result_dir, f"ocr_result_{question_id}_{timestamp}.txt")
                
                # 生成答案图片路径
                answer_image_filename = f"answer_{question_id}_{timestamp}.{file_ext}"
                answer_image_path = os.path.join(answer_images_dir, answer_image_filename)
                
                # 调用Python OCR脚本
                try:
                    # 设置Python路径和OCR脚本路径
                    python_path = "D:\\anaconda3\\envs\\learnerHelper\\python"
                    ocr_script_path = os.path.join(current_app.config['BASE_DIR'], 'app', 'utils', 'ocr_tool.py')
                    
                    # 构建命令
                    command = [
                        python_path,
                        ocr_script_path,
                        file_path,
                        str(question_id),
                        ocr_output_file,
                        answer_image_path
                    ]
                    
                    # 执行命令
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    # 获取输出
                    stdout, stderr = process.communicate()
                    
                    # 检查执行结果
                    if process.returncode != 0:
                        print(f"OCR处理失败: {stderr}")
                    else:
                        # 从OCR结果文件中读取答案
                        if os.path.exists(ocr_output_file):
                            with open(ocr_output_file, 'r', encoding='utf-8') as f:
                                for line in f:
                                    if line.startswith("答案:"):
                                        answer_text = line[3:].strip()
                                        break
                except Exception as e:
                    print(f"OCR处理异常: {str(e)}")
            
            # 创建或更新学生答案
            student_answer, created = StudentAnswer.get_or_create(
                student_id=student_id,
                question_id=question_id,
                defaults={
                    'commit_answer': answer_text,
                    'earned_score': 0,  # 初始得分为0，等待教师批改
                    'work_time': current_time,
                    'answerImagePath': answer_image_path if answer_image_path and os.path.exists(answer_image_path) else file_path
                }
            )
            
            if not created:
                # 如果记录已存在，更新答案和时间
                student_answer.commit_answer = answer_text
                student_answer.work_time = current_time
                student_answer.answerImagePath = answer_image_path if answer_image_path and os.path.exists(answer_image_path) else file_path
                student_answer.save()
            
            # 更新学生作业状态和时间
            update_student_assignment(student_id, question.assignment_id, current_time)
            
            return jsonify(Result.success({
                "submissionId": student_answer.submission_id,
                "status": "已提交",
                "workTime": current_time.strftime("%Y-%m-%d %H:%M:%S")
            }))
        
        else:
            return jsonify(Result.error("未提供答案或文件", 400)), 400
    
    except Exception as e:
        print(f"提交答案失败: {str(e)}")
        return jsonify(Result.error("提交失败，请重试", 500)), 500

def update_student_assignment(student_id, assignment_id, work_time):
    """更新学生作业状态和时间"""
    try:
        # 查询学生作业
        student_assignment = StudentAssignment.get_or_none(
            (StudentAssignment.student_id == student_id) & 
            (StudentAssignment.assignment_id == assignment_id)
        )
        
        if student_assignment:
            # 更新作业状态和时间
            student_assignment.status = "已提交"
            student_assignment.work_time = work_time
            student_assignment.save()
    except Exception as e:
        print(f"更新学生作业状态失败: {str(e)}")