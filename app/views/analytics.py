from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for
from app.services.analytics_service import AnalyticsService
from app.services.course_service import CourseService
from app.services.knowledge_mastery_service import NeuralCDMService
from app.models.user import User, Role,UserRole
from app.models.course import Course,StudentCourse


analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    current_user = User.get_by_id(user_id)
    
    roles = [ur.role.name for ur in current_user.roles]
    print(f"调试信息 - 用户角色: {roles}")  # 添加调试输出
    is_teacher = 'teacher' in roles
    is_admin = 'admin' in roles
   
    
    # 根据角色获取不同的数据
    if is_admin:
        courses = CourseService.get_all_courses()  # 管理员可以看到所有课程
        all_students = (User
                    .select()
                    .join(UserRole)
                    .join(Role)
                    .where(Role.name == 'student'))
        print(f"调试信息 - 管理员查看所有课程和学生: {len(courses)} 课程, {len(all_students)} 学生")
    elif is_teacher:
        courses = CourseService.get_courses_by_teacher(user_id)  # 教师只能看到自己教的课程
        # 获取教师所有课程的学生（去重）
        all_students = (User
                       .select()
                       .join(StudentCourse)
                       .join(Course)
                       .where(Course.teacher == user_id, 
                              StudentCourse.is_active == True)
                       .distinct())

        print(f"{all_students}")
        print(f"调试信息 - 教师查看课程: {len(courses)} 课程, {len(all_students)} 学生")
    else:
        courses = CourseService.get_courses_by_student(user_id)  # 学生只能看到自己选的课程
        all_students = []
    return render_template('analytics/index.html', 
                         is_teacher=is_teacher,
                         is_admin=is_admin,
                         courses=courses,
                         all_students=all_students)

@analytics_bp.route('/student/<int:student_id>')
def student_analytics(student_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    current_user = User.get_by_id(user_id)
    student = User.get_by_id(student_id)
    
    # 获取用户角色
    roles = [ur.role.name for ur in current_user.roles]
    print(f"调试信息 - 用户角色: {roles}")  # 添加调试输出
    is_teacher = 'teacher' in roles
    is_admin = 'admin' in roles
  
    
    # 验证权限
    if user_id != student_id and not is_teacher and not is_admin:
        return redirect(url_for('dashboard.index'))
    
    # 获取可选的课程列表
    if is_admin:
        # 管理员可以看到学生选的所有课程
        courses = CourseService.get_courses_by_student(student_id)
    elif is_teacher:
        # 教师只能看到自己教的课程中该学生选的课程
        teacher_courses = CourseService.get_courses_by_teacher(user_id)
        student_courses = CourseService.get_courses_by_student(student_id)
        courses = list(set(teacher_courses) & set(student_courses))
    else:
        # 学生只能看到自己选的课程
        courses = CourseService.get_courses_by_student(student_id)
    
    # 默认选择第一个课程
    selected_course_id = request.args.get('course_id', None)
    if not selected_course_id and courses:
        selected_course_id = courses[0].id
    
    # 获取学习活动摘要
    activity_summary = AnalyticsService.get_student_activity_summary(
        student_id, 
        course_id=selected_course_id
    )
    
    # 知识点掌握情况
    knowledge_mastery = AnalyticsService.get_student_knowledge_mastery(
        student_id,
        course_id=selected_course_id
    )
    
    # 学习问题检测
    learning_issues = AnalyticsService.detect_learning_issues(
        student_id,
        course_id=selected_course_id
    )
    
    return render_template('analytics/student.html',
                         student=student,
                         courses=courses,
                         selected_course_id=int(selected_course_id) if selected_course_id else None,
                         activity_summary=activity_summary,
                         knowledge_mastery=knowledge_mastery,
                         learning_issues=learning_issues,
                         is_teacher=is_teacher,
                         is_admin=is_admin)

@analytics_bp.route('/course/<int:course_id>')
def course_analytics(course_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    current_user = User.get_by_id(user_id)
    course = Course.get_by_id(course_id)
    
    
    # 获取用户角色
    roles = [ur.role.name for ur in current_user.roles]
    print(f"调试信息 - 用户角色: {roles}")  # 添加调试输出
    is_admin = 'admin' in roles
    
    # 验证权限：管理员或课程教师可以查看
    print(f"调试信息 - 课程教师ID: {course.teacher_id}, 当前用户ID: {user_id}, 是否管理员: {is_admin}")

    if not is_admin and course.teacher_id != user_id:
        return redirect(url_for('dashboard.index'))
    
    # 获取课程学生
    students = CourseService.get_students_by_course(course_id)
    
    # 收集所有学生的知识点掌握数据
    student_masteries = {}
    for student in students:
        mastery = AnalyticsService.get_student_knowledge_mastery(student.id, course_id)
        student_masteries[student.id] = mastery
        # print(f"调试信息 - 学生ID: {student.id}, 知识点掌握数据: {mastery}")
    
    # 计算课程活跃度
    course_activity = {}
    for student in students:
        activity = AnalyticsService.get_student_activity_summary(student.id, course_id)
        course_activity[student.id] = activity
    
    
    # 计算课程所有知识点学生的掌握情况
    course_masteries = AnalyticsService.get_course_knowledge_mastery(course_id, students)
    
    # 获取课程所有知识点
    knowledge_points = AnalyticsService.get_course_knowledge_points(course_id)
    
    
    
    
    return render_template('analytics/course.html',
                         current_user=current_user,
                         course=course,
                         students=students,
                         student_masteries=student_masteries,
                         course_activity=course_activity,
                         course_masteries=course_masteries,
                         knowledge_points=knowledge_points,
                         is_admin=is_admin)


@analytics_bp.route('/course/<int:course_id>/get_suggestions', methods=['GET'])
def get_teaching_suggestions(course_id):
    """获取 AI 教学建议的 API 端点"""
    if 'user_id' not in session:
        return jsonify(success=False, message="未登录"), 401

    user_id = session['user_id']
    current_user = User.get_by_id(user_id)
    course = Course.get_by_id(course_id)

    # 验证权限：管理员或课程教师可以查看
    roles = [ur.role.name for ur in current_user.roles]
    is_admin = 'admin' in roles
    if not is_admin and course.teacher_id != user_id:
        return jsonify(success=False, message="无权限访问该课程"), 403

    # 获取课程学生
    students = CourseService.get_students_by_course(course_id)

    try:
        # 调用 AI 教学建议服务
        teaching_suggestions = AnalyticsService.get_teaching_suggestions(course_id, students)
        return jsonify(success=True, teaching_suggestions=teaching_suggestions)
    except Exception as e:
        return jsonify(success=False, message=f"获取教学建议失败：{str(e)}"), 500


@analytics_bp.route('/record-activity', methods=['POST'])
def record_activity():
    """记录学生学习活动的API端点"""
    if 'user_id' not in session:
        return jsonify(success=False, message="未登录"), 401
    
    data = request.json
    student_id = session['user_id']
    course_id = data.get('course_id')
    activity_type = data.get('activity_type')
    duration = int(data.get('duration', 0))
    knowledge_point_id = data.get('knowledge_point_id')
    metadata = data.get('metadata')
    
    try:
        AnalyticsService.record_learning_activity(
            student_id=student_id,
            course_id=course_id,
            activity_type=activity_type,
            duration=duration,
            knowledge_point_id=knowledge_point_id,
            metadata=metadata
        )
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, message=str(e)), 400

@analytics_bp.route('/course/<int:course_id>/update_mastery', methods=['POST'])
def update_course_mastery(course_id):
    """更新课程知识点掌握度的API端点"""
    if 'user_id' not in session:
        return jsonify(success=False, message="未登录"), 401
    
    user_id = session['user_id']
    course = Course.get_by_id(course_id)
    
    # 验证权限：只有课程教师可以更新
    if course.teacher_id != user_id:
        return jsonify(success=False, message="只有课程教师可以更新知识点掌握度"), 403
    
    try:
        # 创建NeuralCDM服务实例
        service = NeuralCDMService()
        
        # 训练模型
        train_result = service.train_model(course_id, epochs=50, lr=0.001, batch_size=16)
        
        if not train_result['success']:
            return jsonify(success=False, message=train_result['message']), 400
        
        # 更新数据库中的掌握度
        update_result = service.update_database_mastery(course_id)
        
        if not update_result['success']:
            return jsonify(success=False, message=update_result['message']), 400
        
        return jsonify(success=True, message=f"知识点掌握度更新成功！{update_result['message']}")
        
    except Exception as e:
        return jsonify(success=False, message=f"更新失败：{str(e)}"), 500
