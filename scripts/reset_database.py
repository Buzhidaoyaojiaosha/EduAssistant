from app import create_app

app = create_app()

from app.models.user import *
from app.models.course import *
from app.models.assignment import *
from app.models.learning_data import *
from app.models.knowledge_base import *
from app.models.chat import *
# 导入新增模型
from app.models.NewAdd import Question, StudentAnswer, Feedback, WrongBook, QuestionWrongBook


from scripts.create_tables import tables

# 修改这一行，添加cascade=True参数
db.drop_tables(tables, cascade=True)
db.create_tables(tables)

from app.services.user_service import UserService

def initialize_system():
    # 只有在没有任何角色定义时才允许初始化
    if Role.select().count() > 0:
        return
    
    if True:
        # 创建基础角色
        roles = {
            'admin': '系统管理员',
            'teacher': '教师',
            'student': '学生'
        }
        
        for role_name, description in roles.items():
            Role.create(name=role_name, description=description).save()
            
        # 创建管理员账户
        admin_username = 'root'
        admin_password = '123456'
        admin_email = 'admin@example.com'
        admin_name = 'root'
        
        try:
            user_service = UserService()
            admin_user = user_service.create_user(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                name=admin_name,
                role_names=['admin']
            )
            admin_user.save()
            return 
        except ValueError as e:
            print("Error in initializing", str(e))
    
    return

initialize_system()

from scripts.create_test.create_test_users import main as step1
from scripts.create_test.create_courses_knowledge_points import main as step2
from scripts.create_test.create_enrollments_assignments import main as step3
from scripts.create_test.create_learning_activities_mastery import main as step4
from scripts.create_test.create_questions_wrongbooks import main as step5
from scripts.create_test.create_teaching_activity import main as step6

step1()
step2()
step3()
step4()
step5()  # 添加第5步：创建题目、学生答题、教师反馈和错题本数据
step6()  # 创建教师活动数据