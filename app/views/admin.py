from flask import Blueprint, render_template, redirect, url_for, flash, request, session

from app.services.analytics_service import AnalyticsService
from app.services.user_service import UserService
from app.models.user import User, Role, UserRole
from app.models.user import User
from app.models.course import Course
from app.models.assignment import Assignment
from app.models.knowledge_base import KnowledgeBase

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 管理员访问权限检查装饰器
def admin_required(view_func):
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        user = User.get_by_id(session['user_id'])
        if not UserService.has_role(user, 'admin'):
            flash('您没有管理员权限。', 'danger')
            return redirect(url_for('dashboard.index'))
            
        return view_func(*args, **kwargs)
    
    wrapped_view.__name__ = view_func.__name__
    return wrapped_view

@admin_bp.route('/')
@admin_required
def index():
    print("\n--- 进入admin index函数 ---") 
    # 获取真实系统统计数据
    stats = {
        'user_count': User.select().count(),
        'course_count': Course.select().count(),
        'assignment_count': Assignment.select().count(),
        'knowledge_count': KnowledgeBase.select().count()
    }
    
    student_activities = AnalyticsService.get_all_student_activity()
    teacher_activities = AnalyticsService.get_all_teacher_activity()
    
    # 只查有活跃度的学生
    student_ids = list(student_activities.keys())
    students = list(User.select().where(User.id.in_(student_ids)))
    
    teacher_ids = list(teacher_activities.keys())
    teachers = list(User.select().where(User.id.in_(teacher_ids)))
    
    # 预处理图表数据
    student_names = [student.name for student in students]
    student_daily_data = [student_activities[student.id]['daily'] for student in students]
    student_weekly_data = [student_activities[student.id]['weekly'] for student in students]
    
    teacher_names = [teacher.name for teacher in teachers]
    teacher_daily_data = [teacher_activities[teacher.id]['daily'] for teacher in teachers]
    teacher_weekly_data = [teacher_activities[teacher.id]['weekly'] for teacher in teachers]
    
    return render_template(
        'admin/dashboard.html',
        students=students,
        teachers=teachers,
        student_names=student_names,
        student_daily_data=student_daily_data,
        student_weekly_data=student_weekly_data,
        teacher_names=teacher_names,
        teacher_daily_data=teacher_daily_data,
        teacher_weekly_data=teacher_weekly_data,
        **stats
    )


@admin_bp.route('/users')
@admin_required
def users():
    all_users = User.select()
    return render_template('admin/users.html', users=all_users)

# @admin_bp.route('/dashboard')
# def admin_dashboard():
#     # 获取学生活动数据
#     student_activities = AnalyticsService.get_all_student_activity()
#     print(f"学生数据如下:{student_activities}")
#     # 获取教师活动数据
#     # teacher_activities = AnalyticsService.get_all_teacher_activity()

#     return render_template('admin/dashboard.html', 
#                          students=student_activities['students'], 
#                         #  teachers=teacher_activities['teachers'], 
#                          course_activity=student_activities['course_activity']) #| teacher_activities['course_activity'])


@admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.get_by_id(user_id)
    roles = Role.select()
    user_roles = [ur.role.id for ur in user.roles]
    
    if request.method == 'POST':
        # 更新用户信息
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.name = request.form.get('name')
        user.is_active = 'is_active' in request.form
        user.save()
        
        # 更新角色
        UserRole.delete().where(UserRole.user == user).execute()
        for role_id in request.form.getlist('roles'):
            UserRole.create(user=user, role_id=role_id)
            
        flash('用户信息已更新。', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/edit_user.html', user=user, roles=roles, user_roles=user_roles)


@admin_bp.route('/roles')
@admin_required
def roles():
    all_roles = Role.select()
    return render_template('admin/roles.html', roles=all_roles)


@admin_bp.route('/roles/add', methods=['GET', 'POST'])
@admin_required
def add_role():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if Role.select().where(Role.name == name).exists():
            flash(f"角色 '{name}' 已存在。", 'danger')
        else:
            Role.create(name=name, description=description)
            flash('角色已创建。', 'success')
            return redirect(url_for('admin.roles'))
    
    return render_template('admin/add_role.html')


@admin_bp.route('/initialize', methods=['GET', 'POST'])
def initialize_system():
    # 只有在没有任何角色定义时才允许初始化
    if Role.select().count() > 0:
        flash('系统已初始化，无法重新初始化。', 'warning')
        return redirect(url_for('admin.index'))
    
    if request.method == 'POST':
        # 创建基础角色
        roles = {
            'admin': '系统管理员',
            'teacher': '教师',
            'student': '学生'
        }
        
        for role_name, description in roles.items():
            Role.create(name=role_name, description=description)
            
        # 创建管理员账户
        admin_username = request.form.get('admin_username', 'root')
        admin_password = request.form.get('admin_password', '123456')
        admin_email = request.form.get('admin_email', 'admin@example.com')
        admin_name = request.form.get('admin_name', 'root')
        
        try:
            admin_user = UserService.create_user(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                name=admin_name,
                role_names=['admin']
            )
            session['user_id'] = admin_user.id
            session['username'] = admin_user.username
            
            flash('系统初始化完成！已创建管理员账户。', 'success')
            return redirect(url_for('dashboard.index'))
        except ValueError as e:
            flash(str(e), 'danger')
    
    return render_template('admin/initialize.html')


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    try:
        # 获取当前登录用户
        current_user = User.get_by_id(session['user_id'])
        
        # 不能删除自己
        if current_user.id == user_id:
            flash('不能删除当前登录的用户。', 'danger')
            return redirect(url_for('admin.users'))
            
        user = User.get_by_id(user_id)
        username = user.username
        
        # 调用服务层删除用户
     
        success = UserService.delete_user(user_id)
        
        if success:
            flash(f'用户 {username} 已成功删除。', 'success')
        else:
            flash(f'删除用户 {username} 失败。', 'danger')
            
    except User.DoesNotExist:
        flash('用户不存在。', 'danger')
    except Exception as e:
        flash(f'删除用户时出错: {str(e)}', 'danger')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    username = request.form.get('username')
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    is_active = 'is_active' in request.form
    roles = request.form.getlist('roles')
    
    try:
        user = UserService.create_user(
            username=username,
            email=email,
            password=password,
            name=name,
            role_names=roles,  # 注意这里参数名是role_names
          
        )

        flash('用户添加成功', 'success')
        return redirect(url_for('admin.users'))
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.users'))
    except Exception as e:
        flash(f'添加用户失败333: {str(e)}', 'danger')
        return redirect(url_for('admin.users'))
    
@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_password(user_id):
    try:
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证密码是否匹配
        if new_password != confirm_password:
            flash('两次输入的密码不一致，请重新输入', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))
        
        # 获取用户并重置密码
        user = User.get_by_id(user_id)
        UserService.set_password(user, new_password)
        
        flash('密码已成功重置', 'success')
        return redirect(url_for('admin.edit_user', user_id=user_id))
        
    except Exception as e:
        flash(f'重置密码时出错: {str(e)}', 'danger')
        return redirect(url_for('admin.edit_user', user_id=user_id))