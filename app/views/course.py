from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from peewee import JOIN
import io 

from app.services.course_service import CourseService
from app.services.assignment_service import AssignmentService
from app.services.user_service import UserService
from app.services.knowledge_point_service import KnowledgePointService
from app.models.user import User
from app.models.course import Course
from datetime import datetime
from peewee import DoesNotExist
from app.models.course import StudentCourse
from app.models.assignment import Assignment, StudentAssignment
from app.models.NewAdd import Question, StudentAnswer, Feedback, WrongBook, QuestionWrongBook
from app.models.learning_data import (
    KnowledgePoint, AssignmentKnowledgePoint, 
    StudentKnowledgePoint, LearningActivity, 
    KnowledgeBaseKnowledgePoint
)

course_bp = Blueprint('course', __name__, url_prefix='/course')

@course_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = User.get_by_id(user_id)
    
    # 获取搜索关键词
    search_query = request.args.get('q', '').strip()
    
    # 获取课程数据（根据用户角色）
    if UserService.has_role(user, 'teacher'):
        courses = CourseService.get_courses_by_teacher(user_id, search_query)
    else:
        courses = CourseService.get_all_courses(search_query)
    
    return render_template('course/index.html', courses=courses)

@course_bp.route('/create', methods=['GET', 'POST'])
def create():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    user_id = session['user_id']
    user = User.get_by_id(user_id)
    
    if not UserService.has_role(user, 'teacher'):
        flash('只有教师可以创建课程。', 'warning')
        return redirect(url_for('course.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        description = request.form.get('description')
        
        try:
            course = CourseService.create_course(
                name=name,
                code=code,
                description=description,
                teacher_id=user_id
            )
            flash(f'课程 "{name}" 创建成功!', 'success')
            return redirect(url_for('course.view', course_id=course.id))
        except ValueError as e:
            flash(str(e), 'danger')
    
    return render_template('course/create.html')

@course_bp.route('/<int:course_id>/delete', methods=['GET', 'POST'])
def delete(course_id):
    """删除课程及其所有相关数据"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    try:
        course = Course.get_by_id(course_id)
    except Course.DoesNotExist:
        flash('课程不存在。', 'danger')
        return redirect(url_for('course.index'))
    
    # 验证权限 - 只有课程教师可以删除课程
    if course.teacher_id != user_id:
        flash('只有课程教师可以删除课程。', 'warning')
        return redirect(url_for('course.view', course_id=course_id))
    
    if request.method == 'POST':
        try:
            # 导入所需模型
            from peewee import DoesNotExist
            from app.models.course import StudentCourse
            from app.models.assignment import Assignment, StudentAssignment
            from app.models.NewAdd import Question, StudentAnswer, Feedback, WrongBook, QuestionWrongBook
            from app.models.learning_data import (
                KnowledgePoint, AssignmentKnowledgePoint, 
                StudentKnowledgePoint, LearningActivity, 
                KnowledgeBaseKnowledgePoint
            )
            
            # 使用事务确保数据一致性
            with Course._meta.database.atomic():
                # 1. 获取课程相关的基础数据
                course_questions = Question.select().join(Assignment).where(Assignment.course == course)
                course_assignments = Assignment.select().where(Assignment.course == course)
                course_wrong_books = WrongBook.select().where(WrongBook.course == course)
                course_knowledge_points = KnowledgePoint.select().where(KnowledgePoint.course == course)
                
                # 2. 删除错题本相关记录（最深层的关联）
                if course_questions.exists():
                    question_ids = [q.question_id for q in course_questions]
                    # 删除题目与错题本的关联记录
                    QuestionWrongBook.delete().where(
                        QuestionWrongBook.question_id.in_(question_ids)
                    ).execute()
                
                # 删除课程相关的错题本
                if course_wrong_books.exists():
                    wrong_book_ids = [wb.wrong_book_id for wb in course_wrong_books]
                    # 删除错题本中剩余的题目关联（如果有跨课程的情况）
                    QuestionWrongBook.delete().where(
                        QuestionWrongBook.wrong_book_id.in_(wrong_book_ids)
                    ).execute()
                    # 删除错题本本身
                    WrongBook.delete().where(WrongBook.course == course).execute()
                
                # 3. 删除课程相关的反馈记录
                if course_assignments.exists():
                    assignment_ids = [a.id for a in course_assignments]
                    Feedback.delete().where(
                        Feedback.assignment_id.in_(assignment_ids)
                    ).execute()
                
                # 4. 删除课程相关的学生答案记录
                if course_questions.exists():
                    question_ids = [q.question_id for q in course_questions]
                    StudentAnswer.delete().where(StudentAnswer.question_id.in_(question_ids)).execute()
                
                # 5. 删除知识点相关的学习数据
                if course_knowledge_points.exists():
                    knowledge_point_ids = [kp.id for kp in course_knowledge_points]
                    
                    # 删除学生知识点掌握情况
                    StudentKnowledgePoint.delete().where(
                        StudentKnowledgePoint.knowledge_point_id.in_(knowledge_point_ids)
                    ).execute()
                    
                    # 删除知识点与知识库的关联
                    KnowledgeBaseKnowledgePoint.delete().where(
                        KnowledgeBaseKnowledgePoint.knowledge_point_id.in_(knowledge_point_ids)
                    ).execute()
                
                # 6. 删除作业与知识点的关联
                if course_assignments.exists():
                    assignment_ids = [a.id for a in course_assignments]
                    AssignmentKnowledgePoint.delete().where(
                        AssignmentKnowledgePoint.assignment_id.in_(assignment_ids)
                    ).execute()
                
                # 7. 删除课程相关的学习活动记录
                LearningActivity.delete().where(LearningActivity.course == course).execute()
                
                # 8. 删除课程下的所有题目
                Question.delete().where(Question.course == course).execute()
                
                # 9. 删除学生作业记录
                if course_assignments.exists():
                    StudentAssignment.delete().where(
                        StudentAssignment.assignment_id.in_(assignment_ids)
                    ).execute()
                
                # 10. 删除课程作业
                Assignment.delete().where(Assignment.course == course).execute()
                
                # 11. 删除课程知识点（先删除子知识点，再删除父知识点）
                # 获取所有课程知识点，按层级倒序删除
                if course_knowledge_points.exists():
                    # 先删除有父级的知识点（子知识点）
                    child_kps = course_knowledge_points.where(KnowledgePoint.parent_id.is_null(False))
                    for kp in child_kps:
                        kp.delete_instance()
                    
                    # 再删除没有父级的知识点（根知识点）
                    root_kps = course_knowledge_points.where(KnowledgePoint.parent_id.is_null(True))
                    for kp in root_kps:
                        kp.delete_instance()
                
                # 12. 删除学生课程关联记录
                StudentCourse.delete().where(StudentCourse.course == course).execute()
                
                # 13. 最后删除课程本身
                course_name = course.name
                course.delete_instance()
                
                flash(f'课程 "{course_name}" 及其所有相关数据已成功删除。', 'success')
                return redirect(url_for('course.index'))
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(f'删除课程失败: {str(e)}', 'danger')
            return redirect(url_for('course.view', course_id=course_id))
    
    # GET请求 - 显示确认删除页面
    return render_template('course/delete_confirm.html', course=course)
        
@course_bp.route('/<int:course_id>')
def view(course_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    course = Course.get_by_id(course_id)
    user_id = session['user_id']
    user = User.get_by_id(user_id)
    
    # 确认用户是课程的教师或学生
    is_teacher = course.teacher_id == user_id
    is_student = False
    
    if not is_teacher:
        student_courses = CourseService.get_courses_by_student(user_id)
        if course_id in [c.id for c in student_courses]:
            is_student = True
    
    '''if not (is_teacher or is_student):
        flash('您没有访问该课程的权限。', 'warning')
        return redirect(url_for('course.index'))'''
    
    # 获取课程作业
    assignments = AssignmentService.get_course_assignments(course_id)
    
    # 获取课程知识点
    knowledge_points = KnowledgePointService.get_course_knowledge_points(course_id)
    
    # 如果是教师，获取学生列表
    students = None
    if is_teacher:
        students = CourseService.get_students_by_course(course_id)
    
    # 如果是学生，获取个人作业情况
    student_assignments = None
    wrong_questions = []
    if is_student:
        student_assignments = AssignmentService.get_student_assignments(user_id, course_id)
        # 新增错题数据查询
        from app.models.NewAdd import StudentAnswer,Question
        from app.models.assignment import Assignment
        
        # 查询当前课程所有作业及关联题目
        course_assignments = (Assignment
                             .select()
                             .where(Assignment.course == course)
                             .order_by(Assignment.due_date.desc()))
        
        for assignment in course_assignments:
            # 查询该作业的错题（答案错误或得分低于题目分值）
            wrong_answers = (StudentAnswer
                            .select()
                            .join(Question)
                            .where(
                                (StudentAnswer.student == user) &
                                (Question.assignment == assignment) &
                                (
                                    (Question.answer != StudentAnswer.commit_answer) |
                                    (StudentAnswer.earned_score < Question.score) |
                                    (StudentAnswer.earned_score.is_null())
                                )
                            ))
            
            if wrong_answers:
                question_data = []
                for answer in wrong_answers:
                    question_data.append({
                        'id': answer.question.question_id,
                        'question_name': answer.question.question_name,
                        'context': answer.question.context,
                        'answer': answer.question.answer,
                        'student_answer': answer.commit_answer,
                        'score': answer.earned_score or 0,
                        'total_points': answer.question.score,
                        'created_at': answer.work_time or datetime.now()
                    })
                
                wrong_questions.append({
                    'assignment': assignment,
                    'questions': question_data
                })

    return render_template('course/view.html',
                         course=course,
                         is_teacher=is_teacher,
                         is_student=is_student,
                         assignments=assignments,
                         students=students,
                         student_assignments=student_assignments,
                         knowledge_points=knowledge_points,
                         wrong_questions=wrong_questions)

@course_bp.route('/<int:course_id>/enroll', methods=['GET', 'POST'])
def enroll(course_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = User.get_by_id(user_id)
    
    if not UserService.has_role(user, 'student'):
        flash('只有学生可以加入课程。', 'warning')
        return redirect(url_for('course.index'))
    
    course = Course.get_by_id(course_id)
    
    if request.method == 'POST':
        try:
            CourseService.enroll_student(course_id, user_id)
            flash(f'成功加入课程 "{course.name}"!', 'success')
        except ValueError as e:
            flash(str(e), 'warning')
        
        return redirect(url_for('course.view', course_id=course_id))
    
    return render_template('course/enroll.html', course=course)

@course_bp.route('/unenroll/<int:course_id>', methods=['POST'])
def unenroll(course_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # 检查用户是否已加入该课程
    user_id = session['user_id']
    try:
        if CourseService.unenroll_student(course_id, user_id):
            flash(f'您已成功退出课程', 'success')
        else:
            flash(f'退出课程失败', 'warning')
    except Exception as e:
        flash(str(e), 'warning')
    
    return redirect(url_for('course.view', course_id=course_id))


@course_bp.route('/<int:course_id>/assignment/create', methods=['GET', 'POST'])
def create_assignment(course_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    course = Course.get_by_id(course_id)
    
    # 验证权限
    if course.teacher_id != user_id:
        flash('只有课程教师可以创建作业。', 'warning')
        return redirect(url_for('course.view', course_id=course_id))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date = datetime.fromisoformat(request.form.get('due_date'))
        total_points = float(request.form.get('total_points', 100))
        
        assignment = AssignmentService.create_assignment(
            title=title,
            description=description,
            course_id=course_id,
            due_date=due_date,
            total_points=total_points
        )
        
        # 自动分配给所有学生
        assigned_count = AssignmentService.assign_to_students(assignment.id)
        
        flash(f'作业已创建并分配给{assigned_count}名学生。', 'success')
        return redirect(url_for('course.view', course_id=course_id))
    
    return render_template('course/create_assignment.html', course=course)
#查看作业详情页
@course_bp.route('/assignment/<int:assignment_id>')
def view_assignment(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    from app.models.assignment import Assignment, StudentAssignment
    from app.models.NewAdd import Question, Feedback
    
    assignment = Assignment.get_by_id(assignment_id)
    user_id = session['user_id']
    
    # 检查权限
    is_teacher = assignment.course.teacher_id == user_id
    student_assignment = None
    feedback = None  # 新增feedback变量
    
    # 获取作业关联的所有题目
    questions = Question.select(
        Question.question_id,
        Question.question_name,
        Question.context,
        Question.answer,
        Question.score,
        Question.status).where(Question.assignment == assignment).order_by(Question.status)
        
    # 如果是学生，获取学生作业状态和评语
    if not is_teacher:
        student_assignment = StudentAssignment.get_or_none(
            StudentAssignment.student_id == user_id,
            StudentAssignment.assignment_id == assignment_id
        )
        
        # 获取该学生的评语
        if student_assignment:
            feedback = Feedback.get_or_none(
                (Feedback.assignment == assignment) &
                (Feedback.student_id == user_id))
    
    # 如果是教师，获取所有学生提交情况
    submissions = None
    if is_teacher:
        submissions = (StudentAssignment
                      .select()
                      .where(StudentAssignment.assignment_id == assignment_id))
    
    # 获取作业关联的知识点
    knowledge_points = KnowledgePointService.get_assignment_knowledge_points(assignment_id)
    
    # 添加当前时间变量
    now = datetime.now()
    
    return render_template('course/view_assignment.html',
                         assignment=assignment,
                         questions=questions,
                         is_teacher=is_teacher,
                         student_assignment=student_assignment,
                         submissions=submissions,
                         knowledge_points=knowledge_points,
                         now=now,
                         feedback=feedback)  # 直接传递feedback对象

#学生提交作业
@course_bp.route('/assignment/<int:assignment_id>/submit', methods=['POST'])
def submit_assignment(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    try:
        from app.models.NewAdd import StudentAnswer, Question, Feedback  # 添加Feedback导入
        from app.models.assignment import Assignment, StudentAssignment
        from app.models.course import StudentCourse
        from app.services.assignment_service import AssignmentService  # 导入AssignmentService
        
        # 获取作业
        assignment = Assignment.get_by_id(assignment_id)
        
        # 验证学生是否有权限提交此作业
        enrollment = StudentCourse.get_or_none(
            (StudentCourse.student_id == user_id) &
            (StudentCourse.course_id == assignment.course_id)
        )
        
        if not enrollment:
            flash('您没有权限提交此作业。', 'danger')
            return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
        
        # 查找或创建学生作业记录
        student_assignment, created = StudentAssignment.get_or_create(
            student_id=user_id,
            assignment_id=assignment_id
        )
        
        # 检查是否已经提交过
        if student_assignment.status >= 1:
            flash('作业已经提交过，无法重复提交。', 'warning')
            return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
        
        # 获取作业的所有题目
        questions = Question.select().where(Question.assignment_id == assignment_id)
        
        if not questions.exists():
            flash('此作业暂无题目，无法提交。', 'warning')
            return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
        
        # 处理每个题目的答案
        total_score = 0
        answered_count = 0
        answer_details = []  # 用于收集答案详情供AI生成评语
        
        for question in questions:
            answer_key = f'answer_{question.question_id}'
            
            if answer_key in request.form:
                student_answer = request.form.get(answer_key, '').strip()
                
                if not student_answer:
                    continue  # 跳过空答案
                
                answered_count += 1
                # 计算得分（选择题和判断题可以自动评分）
                earned_score = 0
                if question.status == 1:  # 选择题
                    correct_answer = question.answer.strip()
                    if student_answer == correct_answer:
                        earned_score = question.score
                elif question.status == 2:  # 判断题
                    # 转换存储格式：1->"对", 0->"错"
                    stored_answer = "对" if student_answer == "1" or student_answer == "对" else "错"
                    correct_answer = question.answer.strip()
                   
                    print(f"Correct answer for question {question.question_id}: {correct_answer}\n")
                    print(f"Student answer for question {question.question_id}: {stored_answer}\n")
                    if stored_answer == correct_answer:
                        earned_score = question.score
                    student_answer = stored_answer  # 使用转换后的答案进行存储
                else:  # 简答题
                    try:
                        earned_score = AssignmentService.grade_short_answer_with_deepseek(
                            question=question.context,
                            student_answer=student_answer,
                            max_score=question.score
                        )
                    except Exception as e:
                        print(f"AI评分失败: {str(e)}")
                        earned_score = 0
                
                # 存储学生回答
                StudentAnswer.create(
                    student_id=user_id,
                    question_id=question.question_id,
                    commit_answer=student_answer,
                    earned_score=earned_score
                )
                
                total_score += earned_score
                answer_details.append({
                    'question': question.context,  
                    'score': earned_score,
                    'max_score': question.score,
                    'answer': student_answer  
                })
        
        if answered_count == 0:
            flash('请至少回答一道题目。', 'warning')
            return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
        
        # 更新学生作业状态
        student_assignment.work_time = datetime.now()
        student_assignment.status = 1  # 已提交
        student_assignment.final_score = total_score if total_score > 0 else None
        student_assignment.save()
        
        # 调用AI生成评语
        try:
            feedback_content = AssignmentService.generate_feedback_with_deepseek(
                student_answers=answer_details,
                total_score=total_score,
                max_score=assignment.total_points
            )
            
            # 存储评语到Feedback表
            Feedback.create(
                assignment=assignment,
                student_id=user_id,
                comment=feedback_content
            )
        except Exception as e:
            print(f"生成评语失败: {str(e)}")
            # 即使评语生成失败也不影响作业提交
        
        flash(f'作业已成功提交！回答了 {answered_count} 道题目，得分: {total_score}/{assignment.total_points}', 'success')
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'提交作业失败: {str(e)}', 'danger')
    
    return redirect(url_for('course.view_assignment', assignment_id=assignment_id))

#查看提交的作业的作业详情
@course_bp.route('/assignment/<int:assignment_id>/submission/<int:student_id>', methods=['GET'])
def view_submission(assignment_id, student_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    assignment = AssignmentService.get_assignment_by_id(assignment_id)
    from app.models.user import User
    from app.models.assignment import StudentAssignment
    from app.models.NewAdd import StudentAnswer, Question
    
    # 检查权限
    is_teacher = assignment.course.teacher_id == user_id
    is_student = user_id == student_id
    
    if not (is_teacher or is_student):
        flash('您没有权限查看此提交。', 'warning')
        return redirect(url_for('dashboard.index'))
    
    student = User.get_by_id(student_id)
    submission = StudentAssignment.get_or_none(
        StudentAssignment.student==student,
        StudentAssignment.assignment==assignment
    )
    
    if not submission:
        flash('未找到该提交记录。', 'warning')
        return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
    
    # 获取学生的所有答案，按题目顺序排序
    student_answers = (StudentAnswer
                      .select(StudentAnswer, Question)
                      .join(Question)
                      .where(
                          (StudentAnswer.student_id == student_id) &
                          (Question.assignment_id == assignment_id)
                      )
                      .order_by(Question.question_id))

    # 获取评语
    from app.models.NewAdd import Feedback
    feedback = Feedback.get_or_none(
        (Feedback.assignment == assignment) &
        (Feedback.student_id == student_id))
    
    return render_template('course/view_submission.html', 
                          assignment=assignment, 
                          student=student,
                          submission=submission,
                          student_answers=student_answers,
                          is_teacher=is_teacher,
                          feedback=feedback)  # 添加feedback参数

@course_bp.route('/assignment/<int:assignment_id>/grade/<int:student_id>', methods=['POST'])
def grade_assignment(assignment_id, student_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    from app.models.assignment import Assignment
    
    assignment = Assignment.get_by_id(assignment_id)
    
    # 验证权限
    if assignment.course.teacher_id != user_id:
        flash('只有教师可以评分。', 'warning')
        return redirect(url_for('dashboard.index'))
    
    score = float(request.form.get('score', 0))
    feedback = request.form.get("feedback")
    
    try:
        # 更新为使用最终得分
        from app.models.assignment import StudentAssignment
        student_assignment = StudentAssignment.get(
            StudentAssignment.student_id == student_id,
            StudentAssignment.assignment_id == assignment_id
        )
        student_assignment.final_score = score  # 使用final_score而不是score
        student_assignment.feedback = feedback
        student_assignment.status = 2  # 已批改
        student_assignment.save()
        
        flash('评分已保存。', 'success')
    except Exception as e:
        flash(f'评分失败: {str(e)}', 'danger')
    
    return redirect(url_for('course.view_submission', assignment_id=assignment_id, student_id=student_id))

@course_bp.route('/<int:course_id>/knowledge_point/add', methods=['POST'])
def add_knowledge_point(course_id):
    """添加新的知识点到课程中"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    course = Course.get_by_id(course_id)
    
    # 验证权限
    if course.teacher_id != user_id:
        flash('只有课程教师可以添加知识点', 'warning')
        return redirect(url_for('course.view', course_id=course_id))
    
    name = request.form.get('name')
    description = request.form.get('description', '')
    parent_id = request.form.get('parent_id')
    
    # 如果父级ID为空字符串，则设为None
    if parent_id == '':
        parent_id = None
    elif parent_id:
        parent_id = int(parent_id)
    
    try:
        KnowledgePointService.add_knowledge_to_graph(
            name=name,
            course_id=course_id,
            description=description,
            parent_id=parent_id
        )
        flash(f'知识点 "{name}" 创建成功!', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('course.view', course_id=course_id))

@course_bp.route('/<int:course_id>/knowledge_point/edit', methods=['POST'])
def edit_knowledge_point(course_id):
    """编辑课程中的知识点"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    course = Course.get_by_id(course_id)
    
    # 验证权限
    if course.teacher_id != user_id:
        flash('只有课程教师可以编辑知识点', 'warning')
        return redirect(url_for('course.view', course_id=course_id))
    
    knowledge_point_id = int(request.form.get('knowledge_point_id'))
    name = request.form.get('name')
    description = request.form.get('description', '')
    parent_id = request.form.get('parent_id')
    
    # 如果父级ID为空字符串，则设为None
    if parent_id == '':
        parent_id = None
    elif parent_id:
        parent_id = int(parent_id)
    
    try:
        # 获取知识点实例
        knowledge_point = KnowledgePointService.get_knowledge_point(knowledge_point_id)
        
        # 检查知识点是否属于当前课程
        if knowledge_point.course_id != course_id:
            raise ValueError('该知识点不属于当前课程')
        
        # 防止循环引用
        if parent_id and parent_id == knowledge_point_id:
            raise ValueError('知识点不能以自己作为父级')
        
        # 更新知识点
        knowledge_point.name = name
        knowledge_point.description = description
        knowledge_point.parent_id = parent_id
        knowledge_point.save()

        try:
            KnowledgePointService.update_knowledge_point_node(
                kp_id=knowledge_point.id,
                name=name,
                description=description,
                parent_id=parent_id,
                course_id=course_id
            )
        except Exception as e:
            flash(f'图数据库同步失败：{e}', 'warning')
        
        flash(f'知识点 "{name}" 更新成功!', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('course.view', course_id=course_id))

@course_bp.route('/<int:course_id>/knowledge_point/delete', methods=['POST'])
def delete_knowledge_point(course_id):
    """删除课程中的知识点"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    course = Course.get_by_id(course_id)
    
    # 验证权限
    if course.teacher_id != user_id:
        flash('只有课程教师可以删除知识点', 'warning')
        return redirect(url_for('course.view', course_id=course_id))
    
    knowledge_point_id = int(request.form.get('knowledge_point_id'))
    
    try:
        # 获取知识点实例
        from app.models.learning_data import KnowledgePoint
        knowledge_point = KnowledgePointService.get_knowledge_point(knowledge_point_id)
        
        # 检查知识点是否属于当前课程
        if knowledge_point.course_id != course_id:
            raise ValueError('该知识点不属于当前课程')
        
        # 检查是否有子知识点
        children = KnowledgePoint.select().where(KnowledgePoint.parent_id == knowledge_point_id)
        if children.count() > 0:
            raise ValueError('该知识点有子知识点，请先删除或重新分配子知识点')
        
        # 保存名称以供通知
        kp_name = knowledge_point.name
        
        # 删除知识点
        knowledge_point.delete_instance()
        flash(f'知识点 "{kp_name}" 已删除', 'success')

        try:
            KnowledgePointService.delete_knowledge_point_node_from_graph(knowledge_point_id)
        except Exception as e:
            flash(f'图数据库同步失败（删除知识点）: {e}', 'warning')
        

    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('course.view', course_id=course_id))


@course_bp.route('/<int:course_id>/import_knowledge_points', methods=['POST'])
def import_knowledge_points(course_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.get_by_id(session['user_id'])
    course = Course.get_by_id(course_id)
    
    # 验证用户是否为该课程的教师
    if course.teacher_id != user.id:
        flash('只有课程教师可以导入知识点。', 'warning')
        return redirect(url_for('course.view', course_id=course_id))
    
    if 'excel_file' not in request.files:
        flash('未选择文件。', 'warning')
        return redirect(url_for('course.view', course_id=course_id))
    
    file = request.files['excel_file']
    if file.filename == '':
        flash('未选择文件。', 'warning')
        return redirect(url_for('course.view', course_id=course_id))
    
    if file:
        try:
            # 读取文件内容到内存
            file_content = file.read()
            file_stream = io.BytesIO(file_content)
        
        # 先导入到PostgreSQL，获取名称到ID的映射
            id_cache = KnowledgePointService.import_excel_to_knowledge_points(file_stream, course_id)
        
        # 重置文件流指针
            file_stream.seek(0)
        
        # 再导入到Neo4j，传递ID映射
            KnowledgePointService.excel_to_knowledge_point_graph(file_stream, course_id, id_cache)
           
            flash('知识点导入成功。', 'success')
        except Exception as e:
            flash(f'知识点导入失败: {str(e)}', 'danger')
        
        return redirect(url_for('course.view', course_id=course_id))


@course_bp.route('/<int:course_id>/view_knowledge_graph')
def view_knowledge_graph(course_id):
    course = Course.get_by_id(course_id)
    return render_template('course/graph.html', course_id=course_id, course_name=course.name)



@course_bp.route('/assignment/<int:assignment_id>/knowledge_points', methods=['GET', 'POST'])
def assignment_knowledge_points(assignment_id):
    """管理作业关联的知识点"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    from app.models.assignment import Assignment
    
    assignment = Assignment.get_by_id(assignment_id)
    course_id = assignment.course_id
    user_id = session['user_id']
    
    # 验证权限
    if assignment.course.teacher_id != user_id:
        flash('只有课程教师可以管理作业知识点', 'warning')
        return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
    
    if request.method == 'POST':
        # 获取提交的知识点ID列表
        knowledge_point_ids = request.form.getlist('knowledge_point_ids', type=int)
        
        # 获取权重
        weights = {}
        for kp_id in knowledge_point_ids:
            weight = request.form.get(f'weight_{kp_id}', 1.0, type=float)
            weights[kp_id] = weight
        
        try:
            # 清除旧的关联并添加新的
            from app.models.learning_data import AssignmentKnowledgePoint
            AssignmentKnowledgePoint.delete().where(
                AssignmentKnowledgePoint.assignment_id == assignment_id
            ).execute()
            
            if knowledge_point_ids:
                KnowledgePointService.add_knowledge_points_to_assignment(
                    assignment_id, knowledge_point_ids, weights
                )
            
            flash('作业知识点关联已更新', 'success')
        except ValueError as e:
            flash(str(e), 'danger')
        
        return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
    
    # 获取课程所有知识点
    course_knowledge_points = KnowledgePointService.get_course_knowledge_points(course_id)
    
    # 获取作业已关联的知识点
    assignment_knowledge_points = KnowledgePointService.get_assignment_knowledge_points(assignment_id)
    
    return render_template('course/assignment_knowledge_points.html',
                          assignment=assignment,
                          course_knowledge_points=course_knowledge_points,
                          assignment_knowledge_points=assignment_knowledge_points)

@course_bp.route('/assignment/<int:assignment_id>/add-question', methods=['GET', 'POST'])
def add_question(assignment_id):
    from app.models.assignment import Assignment
    from app.models.course import Course
    assignment = Assignment.get_by_id(assignment_id)
    course = assignment.course
    
    # 验证权限
    user_id = session['user_id']
    if assignment.course.teacher_id != user_id:
        flash('只有课程教师可以添加题目', 'warning')
        return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            question_type = int(request.form.get('type', 0))
            answer = request.form.get('answer', '').strip()
            
            # 如果是判断题，转换答案格式
            if question_type == 2:  # 判断题
                if answer == '1':
                    answer = '对'
                elif answer == '0':
                    answer = '对'
                else:
                    # 如果输入的不是1或0，但题目类型是判断题，给出错误提示
                    flash('判断题答案只能是1(对)或0(错)', 'danger')
                    return render_template('course/add_question.html', assignment=assignment)
            print(f"Processed answer for question type {question_type}: {answer}\n")
            # 创建题目
            question = Question.create(
                assignment=assignment,
                course=course,
                question_name=request.form.get('name'),
                context=request.form.get('context'),
                answer=answer,  # 使用转换后的答案
                analysis=request.form.get('analysis'),
                score=float(request.form.get('score', 10.0)),
                status=question_type
            )
            
            # 更新作业总分
            AssignmentService.update_assignment_total_points(assignment_id)
            
            flash('题目添加成功', 'success')
            return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
        except Exception as e:
            flash(f'添加题目失败: {str(e)}', 'danger')
    
    return render_template('course/add_question.html', assignment=assignment)

@course_bp.route('/question/<int:question_id>/edit', methods=['GET', 'POST'])
def edit_question(question_id):
    question = Question.get_by_id(question_id)
    user_id = session['user_id']
    # 验证权限
    if question.assignment.course.teacher_id != user_id:
        flash('只有课程教师可以更新题目', 'warning')
        return redirect(url_for('course.view_assignment', assignment_id=question.assignment_id))
    
    if request.method == 'POST':
        try:
            # 保存旧的分数用于比较
            old_score = question.score
            
            question.question_name = request.form.get('name')
            question.context = request.form.get('context')
            question.answer = request.form.get('answer')
            question.score = float(request.form.get('score'))
            question.status = int(request.form.get('type'))
            question.save()
            
            # 如果分数有变化，更新作业总分
            if old_score != question.score:
                AssignmentService.update_assignment_total_points(question.assignment.id)
            
            flash('题目更新成功', 'success')
            return redirect(url_for('course.view_assignment', assignment_id=question.assignment.id))
        except Exception as e:
            flash(f'更新题目失败: {str(e)}', 'danger')
    
    return render_template('course/edit_question.html', question=question)

@course_bp.route('/question/<int:question_id>/delete', methods=['POST'])
def delete_question(question_id):
    """删除题目并更新作业总分"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    try:
        question = Question.get_by_id(question_id)
        assignment_id = question.assignment.id
        
        # 验证权限
        if question.assignment.course.teacher_id != user_id:
            flash('只有课程教师可以删除题目', 'warning')
            return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
        
        # 删除题目
        question.delete_instance()
        
        # 更新作业总分
        AssignmentService.update_assignment_total_points(assignment_id)
        
        flash('题目已成功删除', 'success')
    except Exception as e:
        flash(f'删除题目失败: {str(e)}', 'danger')
    
    return redirect(url_for('course.view_assignment', assignment_id=assignment_id))

@course_bp.route('/assignment/<int:assignment_id>/grade_student/<int:student_id>', methods=['GET'])
def grade_student_assignment(assignment_id, student_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    from app.models.assignment import Assignment, StudentAssignment
    from app.models.NewAdd import StudentAnswer, Question
    from app.models.user import User
    
    assignment = Assignment.get_by_id(assignment_id)
    
    # 验证权限
    if assignment.course.teacher_id != user_id:
        flash('只有教师可以评分作业。', 'warning')
        return redirect(url_for('dashboard.index'))
    
    student = User.get_by_id(student_id)
    
    # 获取学生作业记录
    student_assignment = StudentAssignment.get_or_none(
        StudentAssignment.student_id == student_id,
        StudentAssignment.assignment_id == assignment_id
    )
    
    if not student_assignment or student_assignment.status == 0:
        flash('该学生尚未提交作业。', 'warning')
        return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
    
    # 获取学生的所有答案
    student_answers = StudentAnswer.select().join(Question).where(
        (StudentAnswer.student_id == student_id) &
        (Question.assignment_id == assignment_id)
    )
    
    # 获取评语
    feedback = Feedback.get_or_none(
        (Feedback.assignment_id == assignment_id) &
        (Feedback.student_id == student_id)
    )
    
    return render_template('course/grade_assignment.html', 
                          assignment=assignment,
                          student=student,
                          student_assignment=student_assignment,
                          student_answers=student_answers,
                          feedback=feedback)  # 传递feedback对象到模板

# 老师再次评分和写评语
@course_bp.route('/assignment/<int:assignment_id>/grade_student/<int:student_id>', methods=['POST'])
def grade_student_answers(assignment_id, student_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    from app.models.assignment import Assignment, StudentAssignment
    from app.models.NewAdd import StudentAnswer, Question, Feedback  # 添加Feedback导入
    
    assignment = Assignment.get_by_id(assignment_id)
    
    # 验证权限
    if assignment.course.teacher_id != user_id:
        flash('只有教师可以评分作业。', 'warning')
        return redirect(url_for('dashboard.index'))
    
    try:
        # 1. 处理每道题的评分
        student_answers = (StudentAnswer
                          .select(StudentAnswer, Question)
                          .join(Question)
                          .where(
                              (StudentAnswer.student_id == student_id) &
                              (Question.assignment_id == assignment_id)
                          ))
        
        total_score = 0
        for answer in student_answers:
            score_key = f'score_{answer.submission_id}'
            if score_key in request.form:
                score = float(request.form.get(score_key, 0))
                answer.earned_score = score
                answer.save()
                total_score += score
        
        # 2. 更新学生作业记录
        student_assignment = StudentAssignment.get(
            StudentAssignment.student_id == student_id,
            StudentAssignment.assignment_id == assignment_id
        )
        student_assignment.final_score = total_score
        student_assignment.status = 2  # 已批改
        student_assignment.save()
        
        # 3. 处理评语（使用Feedback类）
        feedback_text = request.form.get('feedback', '').strip()
        if feedback_text:  # 只有评语不为空时才处理
            # 查找是否已有评语记录
            try:
                feedback = Feedback.get(
                    (Feedback.assignment == assignment) &
                    (Feedback.student_id == student_id)
                )
                # 更新现有评语
                feedback.comment = feedback_text
                feedback.save()
            except Feedback.DoesNotExist:
                # 创建新评语记录
                Feedback.create(
                    assignment=assignment,
                    student_id=student_id,
                    comment=feedback_text
                )
        
        flash('评分和评语已保存。', 'success')
    except Exception as e:
        flash(f'评分失败: {str(e)}', 'danger')
    
    return redirect(url_for('course.view_assignment', assignment_id=assignment_id))