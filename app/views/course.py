from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from peewee import JOIN

from app.services.course_service import CourseService
from app.services.assignment_service import AssignmentService
from app.services.user_service import UserService
from app.services.knowledge_point_service import KnowledgePointService
from app.models.user import User
from app.models.course import Course
from app.models.NewAdd import Question
from datetime import datetime

course_bp = Blueprint('course', __name__, url_prefix='/course')

@course_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = User.get_by_id(user_id)
    
    if UserService.has_role(user, 'teacher'):
        courses = CourseService.get_courses_by_teacher(user_id)
    else:
        courses = CourseService.get_all_courses()
        
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

@course_bp.route('/assignment/<int:assignment_id>')
def view_assignment(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    from app.models.assignment import Assignment, StudentAssignment
    
    assignment = Assignment.get_by_id(assignment_id)
    user_id = session['user_id']
    
    # 检查权限
    is_teacher = assignment.course.teacher_id == user_id
    student_assignment = None
    
    # 获取作业关联的所有题目 - 修改查询以包含question_id
    questions = Question.select(
        Question.question_id,  # 确保包含题目ID
        Question.question_name,
        Question.context,
        Question.answer,
        Question.score,
        Question.status).where(Question.assignment == assignment).order_by(Question.status)
        
    # 如果是学生，获取学生作业状态
    if not is_teacher:
        student_assignment = StudentAssignment.get_or_none(
            StudentAssignment.student_id == user_id,
            StudentAssignment.assignment_id == assignment_id
        )
        '''if not student_assignment:
            flash('您没有访问该作业的权限。', 'warning')
            return redirect(url_for('course.index'))'''
    
    # 如果是教师，获取所有学生提交情况
    submissions = None
    if is_teacher:
        submissions = StudentAssignment.select().where(
            StudentAssignment.assignment_id == assignment_id
        )
    
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
                         now=now)  # 传递当前时间到模板

@course_bp.route('/assignment/<int:assignment_id>/submit', methods=['POST'])
def submit_assignment(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    try:
        from app.models.NewAdd import StudentAnswer, Question
        from app.models.assignment import Assignment, StudentAssignment
        from app.models.course import StudentCourse
        
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
        
        # 记录表单数据，用于调试
        form_data = dict(request.form)
        print(f"提交的表单数据: {form_data}")
        
        # 删除该学生之前可能存在的答案记录（防止重复）
        try:
            StudentAnswer.delete().where(
                (StudentAnswer.student_id == user_id) &
                (StudentAnswer.question_id.in_([q.question_id for q in questions]))
            ).execute()
        except Exception as e:
            print(f"删除旧答案时出错: {str(e)}")
            # 继续处理，不中断
        
        # 处理每个题目的答案
        total_score = 0
        answered_count = 0
        
        for question in questions:
            answer_key = f'answer_{question.question_id}'
            print(f"检查题目 {question.question_id} 的答案，键名: {answer_key}")
            
            if answer_key in request.form:
                student_answer = request.form.get(answer_key, '').strip()
                print(f"题目 {question.question_id} 的答案: {student_answer}")
                
                if not student_answer:
                    print(f"题目 {question.question_id} 的答案为空，跳过")
                    continue  # 跳过空答案
                
                answered_count += 1
                
                # 计算得分（选择题和判断题可以自动评分）
                earned_score = 0
                if question.status in [1, 2]:  # 选择题或判断题
                    correct_answer = question.answer.strip()
                    print(f"题目 {question.question_id} 的正确答案: {correct_answer}")
                    if student_answer == correct_answer:
                        earned_score = question.score
                
                # 存储学生回答
                try:
                    StudentAnswer.create(
                        student_id=user_id,
                        question_id=question.question_id,
                        commit_answer=student_answer,
                        earned_score=earned_score
                    )
                    print(f"已保存题目 {question.question_id} 的答案")
                except Exception as e:
                    print(f"保存题目 {question.question_id} 的答案时出错: {str(e)}")
                
                total_score += earned_score
        
        print(f"总共回答了 {answered_count} 道题目")
        if answered_count == 0:
            flash('请至少回答一道题目。', 'warning')
            return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
        
        # 更新学生作业状态
        student_assignment.work_time = datetime.now()
        student_assignment.status = 1  # 已提交
        student_assignment.final_score = total_score if total_score > 0 else None  # 使用final_score而不是score
        student_assignment.save()
        
        flash(f'作业已成功提交！回答了 {answered_count} 道题目。', 'success')
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'提交作业失败: {str(e)}', 'danger')
    
    return redirect(url_for('course.view_assignment', assignment_id=assignment_id))

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

    return render_template('course/view_submission.html', 
                          assignment=assignment, 
                          student=student,
                          submission=submission,
                          student_answers=student_answers,
                          is_teacher=is_teacher)

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
        knowledge_point = KnowledgePointService.create_knowledge_point(
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
    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('course.view', course_id=course_id))

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
    course=assignment.course
    # 验证权限
    user_id = session['user_id']
    if assignment.course.teacher_id != user_id:
        flash('只有课程教师可以添加题目', 'warning')
        return redirect(url_for('course.view_assignment', assignment_id=assignment_id))
    if request.method == 'POST':
        try:
            question = Question.create(
                assignment=assignment,
                course=course,
                question_name=request.form.get('name'),
                context=request.form.get('context'),
                answer=request.form.get('answer'),
                analysis=request.form.get('analysis'),
                score=float(request.form.get('score', 10.0)),
                status=int(request.form.get('type', 0))
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
    
    return render_template('course/grade_assignment.html', 
                          assignment=assignment,
                          student=student,
                          student_assignment=student_assignment,
                          student_answers=student_answers)

@course_bp.route('/assignment/<int:assignment_id>/grade_student/<int:student_id>', methods=['POST'])
def grade_student_answers(assignment_id, student_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    from app.models.assignment import Assignment, StudentAssignment
    from app.models.NewAdd import StudentAnswer, Question
    
    assignment = Assignment.get_by_id(assignment_id)
    
    # 验证权限
    if assignment.course.teacher_id != user_id:
        flash('只有教师可以评分作业。', 'warning')
        return redirect(url_for('dashboard.index'))
    
    try:
        # 修正查询方式：使用JOIN来正确关联Question表
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
        
        # 更新学生作业记录
        student_assignment = StudentAssignment.get(
            StudentAssignment.student_id == student_id,
            StudentAssignment.assignment_id == assignment_id
        )
        
        student_assignment.final_score = total_score  # 使用final_score而不是score
        student_assignment.feedback = request.form.get('feedback', '')
        student_assignment.status = 2  # 已批改
        student_assignment.save()
        
        flash('评分已保存。', 'success')
    except Exception as e:
        flash(f'评分失败: {str(e)}', 'danger')
    
    return redirect(url_for('course.view_assignment', assignment_id=assignment_id))