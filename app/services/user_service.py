from werkzeug.security import generate_password_hash, check_password_hash
from app.models.user import User, Role, UserRole
from app.models.course import *
from app.models.knowledge_base import *
from app.models.NewAdd import *
from app.models.learning_data import *
from app.models.assignment import *
from app.models.user import User
from app.services.course_service import CourseService

class UserService:
    """用户服务类，处理用户认证、注册和用户管理。
    
    该服务提供用户账户相关的所有功能，包括创建用户、验证用户凭证、
    用户角色分配和管理等操作。
    """
    
    @staticmethod
    def create_user(username, email, password, name, role_names=None):
        """创建新用户。
        
        Args:
            username (str): 用户名
            email (str): 电子邮件地址
            password (str): 用户密码
            name (str): 用户真实姓名
            role_names (list): 角色名称列表，默认为None
            
        Returns:
            User: 创建的用户对象
            
        Raises:
            ValueError: 如果用户名或邮箱已存在
        """
      
        # 检查用户名是否已存在
        if User.select().where(User.username == username).exists():
            raise ValueError(f"用户名 '{username}' 已存在")
       
        
        # 检查邮箱是否已存在
        if User.select().where(User.email == email).exists():
            raise ValueError(f"邮箱 '{email}' 已被注册")
       
        # 创建用户
        user = User.create(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            name=name
        )
        print(f"用户 {username} 创建成功，ID: {user.id}")
        # 分配角色
        if role_names:
            for role_name in role_names:
                role = Role.get_or_none(Role.name == role_name)
                if role:
                    UserRole.create(user=user, role=role)
      
        return user
    
    @staticmethod
    def authenticate_user(username, password):
        """验证用户凭证。
        
        Args:
            username (str): 用户名
            password (str): 密码
            
        Returns:
            User or None: 如果验证成功返回用户对象，否则返回None
        """
        user = User.get_or_none(User.username == username, User.is_active == True)
        
        if user is not None and check_password_hash(user.password_hash, password):
            return user
            
        return None
    
    @staticmethod
    def get_user_roles(user):
        """获取用户角色列表。
        
        Args:
            user (User): 用户对象
            
        Returns:
            list: 用户角色对象列表
        """
        return [ur.role for ur in user.roles]
    
    @staticmethod
    def has_role(user, role_name):
        """检查用户是否拥有指定角色。
        
        Args:
            user (User): 用户对象
            role_name (str): 角色名称
            
        Returns:
            bool: 如果用户拥有指定角色则返回True，否则返回False
        """
        return UserRole.select().join(Role).where(
            (UserRole.user == user) & (Role.name == role_name)
        ).exists()

    @staticmethod
    def get_user_info(user_id):
        """获取用户信息。
        
        Args:
            user_id (int): 用户ID
        """
        user = User.get_or_none(User.id == user_id)
        if user:
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "name": user.name,
                "roles": [ur.role.name for ur in user.roles],
                "is_active": user.is_active
            }
        return None
    @staticmethod
    def delete_user(user_id):
        """彻底删除用户及其所有相关数据（区分老师、学生、管理员）
        
        Args:
            user_id (int): 要删除的用户ID
            
        Returns:
            bool: 删除是否成功
            
        Raises:
            DoesNotExist: 如果用户不存在
        """
        try:
            user = User.get_by_id(user_id)
            
 
            
            # 1. 更可靠的角色检查方式
            print(f"调试信息 - 正在删除用户: {user.username}, ID: {user.id}")
            roles = [ur.role.name for ur in user.roles]
            print(f"调试信息 - 用户角色: {roles}")  # 添加调试输出
            is_teacher = 'teacher' in roles
            is_student = 'student' in roles
            is_admin = 'admin' in roles
            
            print(f"调试信息 - 用户角色: {roles}")  # 添加调试输出

            # 如果是管理员，直接删除用户本身（不处理其他关联数据）
            if is_admin and not (is_teacher or is_student):
                # 只需删除用户角色关联和用户本身
                UserRole.delete().where(UserRole.user == user).execute()
                user.delete_instance()
                return True

            # 2. 删除用户角色关联
            UserRole.delete().where(UserRole.user == user).execute()
           
            print(f"{is_teacher}{is_student} {is_admin}")
            if is_teacher:
                
                # 3.1 删除老师教授的课程及相关数据
                courses = Course.select().where(Course.teacher == user)
                for course in courses:
                    # 使用之前编写的delete_course函数彻底删除课程
                    CourseService.delete_course(course.id)

            if is_student:
                # 4. 删除学生的学习活动记录
                LearningActivity.delete().where(LearningActivity.student == user).execute()
                
                # 5. 删除学生知识点掌握度
                StudentKnowledgePoint.delete().where(StudentKnowledgePoint.student == user).execute()
                
                # 6. 删除学生作业记录
                StudentAssignment.delete().where(StudentAssignment.student == user).execute()
                
                # 7. 删除学生答案记录
                StudentAnswer.delete().where(StudentAnswer.student == user).execute()
                AiQuestionStudentAnswer.delete().where(AiQuestionStudentAnswer.student == user).execute()
                
                # 8. 删除学生错题本
                WrongBook.delete().where(WrongBook.student == user).execute()
                
                # 9. 删除学生课程关联
                StudentCourse.delete().where(StudentCourse.student == user).execute()
                
                # 10. 删除学生反馈
                Feedback.delete().where(Feedback.student == user).execute()

            # 11. 最后删除用户本身
            user.delete_instance()
            return True
            
        except Exception as e:
            # 记录错误日志
            print(f"删除用户失败: {str(e)}")
            return False
        
    @classmethod
    def set_password(cls, user, password):
        """设置用户密码"""
        user.password_hash = generate_password_hash(password)  # 使用Flask的werkzeug.security中的generate_password_hash
        user.save()