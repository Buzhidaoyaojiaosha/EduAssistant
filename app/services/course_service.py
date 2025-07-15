from app.models.course import *
from app.models.knowledge_base import *
from app.models.NewAdd import *
from app.models.learning_data import *
from app.models.assignment import *
from app.models.user import User
from app.react.tools_register import register_as_tool


class CourseService:
    """课程服务类，处理课程管理和学生课程关联。
    
    该服务提供课程相关的所有功能，包括课程创建、修改、删除，
    以及学生与课程之间的关联管理等。
    """
    @staticmethod
    def create_course(name, code, description, teacher_id):
        """创建新课程。
        
        Args:
            name (str): 课程名称
            code (str): 课程代码
            description (str): 课程描述
            teacher_id (int): 教师用户ID
            
        Returns:
            Course: 创建的课程对象
            
        Raises:
            ValueError: 如果课程代码已存在
        """
        if Course.select().where(Course.code == code).exists():
            raise ValueError(f"课程代码 '{code}' 已存在")
        
        teacher = User.get_by_id(teacher_id)
        return Course.create(
            name=name,
            code=code,
            description=description,
            teacher=teacher
        )
    
    @staticmethod
    def enroll_student(course_id, student_id):
        """将学生加入课程。
        
        Args:
            course_id (int): 课程ID
            student_id (int): 学生ID
            
        Returns:
            StudentCourse: 创建的学生-课程关联对象
            
        Raises:
            ValueError: 如果学生已加入该课程
        """
        if StudentCourse.select().where(
            (StudentCourse.course_id == course_id) & 
            (StudentCourse.student_id == student_id)
        ).exists():
            raise ValueError("学生已加入该课程")
        
        student = User.get_by_id(student_id)
        course = Course.get_by_id(course_id)
        for assignment in course.assignments:
            StudentAssignment.create(
                student=student,
                assignment=assignment,
                status="0",
                total_score=assignment.total_points
            ).save()

        return StudentCourse.create(
            course_id=course_id,
            student_id=student_id
        )
    
    @staticmethod
    def unenroll_student(course_id, student_id):
        """将学生从课程删除。
        
        Args:
            course_id (int): 课程ID
            student_id (int): 学生ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            DoesNotExist: 如果学生没有加入课程
        """
        student_course = StudentCourse.select().where(
            (StudentCourse.course_id == course_id) & 
            (StudentCourse.student_id == student_id)
        ).get()

        for assignment in student_course.course.assignments:
            StudentAssignment.delete().where(
                StudentAssignment.student==student_id,
                StudentAssignment.assignment==assignment
            ).execute()

        return student_course.delete_instance()

    @staticmethod
    def get_courses_by_teacher(teacher_id, search_query=None):
        """获取教师创建的课程，支持模糊搜索"""
        query = Course.select().where(Course.teacher_id == teacher_id)
        
        if search_query:
            # 使用 OR 连接多个字段的模糊匹配
            query = query.where(
                (Course.name.contains(search_query)) |
                (Course.code.contains(search_query)) |
                (Course.description.contains(search_query))
            )
        
        return query.order_by(Course.created_at.desc())
    
    @staticmethod
    def get_all_courses(search_query=None):
        """获取所有课程，支持模糊搜索"""
        query = Course.select()
        
        if search_query:
            query = query.where(
                (Course.name.contains(search_query)) |
                (Course.code.contains(search_query)) |
                (Course.description.contains(search_query))
            )
        
        return query.order_by(Course.created_at.desc())
    
    @register_as_tool(roles=["student", "teacher"])
    @staticmethod
    def get_courses_by_student(student_id):
        """获取学生所参与的所有课程。
        
        Args:
            student_id (int): 学生用户ID
            
        Returns:
            list: 课程对象列表
        """
        return list(Course.select()
                   .join(StudentCourse)
                   .where(StudentCourse.student_id == student_id))
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def get_students_by_course(course_id):
        """获取参与课程的所有学生。
        
        Args:
            course_id (int): 课程ID
            
        Returns:
            list: 学生用户对象列表
        """
        return list(User.select()
                   .join(StudentCourse)
                   .where(StudentCourse.course_id == course_id))

    @staticmethod
    def get_knowledge_base_by_course(course_id, search_query=None):
        """获取与课程相关的知识库条目。
        
        Args:
            course_id (int): 课程ID
            search_query (str, optional): 搜索关键词. Defaults to None.
            
        Returns:
            list: 知识库条目列表
        """
        query = KnowledgeBase.select().where(KnowledgeBase.course_id == course_id)
        
        if search_query:
            query = query.where(
                (KnowledgeBase.title.contains(search_query)) |
                (KnowledgeBase.content.contains(search_query)) |
                (KnowledgeBase.keywords.contains(search_query)))
        
        return query.order_by(KnowledgeBase.created_at.desc())
 
 
    @staticmethod
    def delete_course(course_id):
        """彻底删除课程及其所有相关数据
        
        Args:
            course_id (int): 要删除的课程ID
            
        Returns:
            int: 删除的记录数
            
        Raises:
            DoesNotExist: 如果课程不存在
        """
        try:
            course = Course.get_by_id(course_id)
            print(f"正在删除课程: {course.name} (ID: {course.id})")

            # 1. 删除学习活动记录（必须先于知识点删除）
            deleted_activities = LearningActivity.delete().where(
                (LearningActivity.course_id == course_id) |
                (LearningActivity.knowledge_point_id.in_(
                    KnowledgePoint.select(KnowledgePoint.id).where(KnowledgePoint.course_id == course_id)
                ))).execute()
            print(f"已删除 {deleted_activities} 条学习活动记录")

            # 2. 删除课程相关的知识点和知识条目
            # 先删除知识库条目与知识点的关联
            deleted_kb_links = KnowledgeBaseKnowledgePoint.delete().where(
                KnowledgeBaseKnowledgePoint.knowledge_base_id.in_(
                    KnowledgeBase.select(KnowledgeBase.id).where(KnowledgeBase.course_id == course_id)
                )).execute()
            print(f"已删除 {deleted_kb_links} 条知识库-知识点关联")

            # 删除知识库条目
            deleted_knowledge_bases = KnowledgeBase.delete().where(
                KnowledgeBase.course_id == course_id).execute()
            print(f"已删除 {deleted_knowledge_bases} 条知识库记录")

            # 3. 删除知识点相关数据
            # 先删除学生知识点掌握度
            deleted_knowledge_points = StudentKnowledgePoint.delete().where(
                StudentKnowledgePoint.knowledge_point_id.in_(
                    KnowledgePoint.select(KnowledgePoint.id).where(KnowledgePoint.course_id == course_id)
                )).execute()
            print(f"已删除 {deleted_knowledge_points} 条学生知识点记录")

            # 删除作业与知识点的关联
            deleted_assignment_kps = AssignmentKnowledgePoint.delete().where(
                AssignmentKnowledgePoint.knowledge_point_id.in_(
                    KnowledgePoint.select(KnowledgePoint.id).where(KnowledgePoint.course_id == course_id)
                )).execute()
            print(f"已删除 {deleted_assignment_kps} 条作业-知识点关联")

            # 删除知识点本身
            deleted_kps = KnowledgePoint.delete().where(
                KnowledgePoint.course_id == course_id).execute()
            print(f"已删除 {deleted_kps} 条知识点记录")

            # 4. 删除课程相关的作业、题目、学生答案和AI生成题目
            assignments = Assignment.select().where(Assignment.course_id == course_id)
            total_assignments = assignments.count()
            print(f"准备删除 {total_assignments} 个作业")

            for i, assignment in enumerate(assignments, 1):
                print(f"\n处理作业 {i}/{total_assignments} (ID: {assignment.id}, 标题: {assignment.title})")

                # 首先删除依赖此作业的反馈记录
                deleted_feedbacks = Feedback.delete().where(
                    Feedback.assignment == assignment
                ).execute()
                print(f"已删除 {deleted_feedbacks} 条反馈记录")

                # 删除学生作业记录
                deleted_student_assignments = StudentAssignment.delete().where(
                    StudentAssignment.assignment_id == assignment.id).execute()
                print(f"已删除 {deleted_student_assignments} 条学生作业记录")

                # 删除作业相关的题目
                questions = Question.select().where(Question.assignment_id == assignment.id)
                total_questions = questions.count()
                print(f"准备删除 {total_questions} 个题目")

                for j, question in enumerate(questions, 1):
                    if not question.question_id:
                        print(f"跳过无效题目 (索引 {j})")
                        continue

                    print(f"处理题目 {j}/{total_questions} (ID: {question.question_id})")
                    
                    # 删除题目相关的学生答案
                    deleted_answers = StudentAnswer.delete().where(
                        StudentAnswer.question_id == question.question_id).execute()
                    print(f"已删除 {deleted_answers} 条学生答案")

                    # 删除AI生成的题目及其学生答案
                    ai_questions = AIQuestion.select().where(
                        AIQuestion.original_question_id == question.question_id)
                    total_ai_questions = ai_questions.count()
                    print(f"准备删除 {total_ai_questions} 个AI生成题目")

                    for ai_question in ai_questions:
                        deleted_ai_answers = AiQuestionStudentAnswer.delete().where(
                            AiQuestionStudentAnswer.ai_question_id == ai_question.ai_question_id).execute()
                        print(f"已删除 {deleted_ai_answers} 条AI题目答案")
                        ai_question.delete_instance()

                    # 删除题目本身
                    question.delete_instance()
                    print(f"题目 ID {question.question_id} 已删除")

                # 删除作业本身
                assignment.delete_instance()
                print(f"作业 ID {assignment.id} 已删除")

            # 5. 删除错题本相关数据
            deleted_wrong_books = WrongBook.delete().where(
                WrongBook.course_id == course_id).execute()
            print(f"已删除 {deleted_wrong_books} 条错题本记录")

           

            # 6. 删除学生课程关联
            deleted_student_courses = StudentCourse.delete().where(
                StudentCourse.course_id == course_id).execute()
            print(f"已删除 {deleted_student_courses} 条学生-课程关联")

            # 7. 最后删除课程本身
            course.delete_instance()
            print(f"课程 ID {course.id} 已成功删除")
            return True

        except Exception as e:
            print(f"\n删除课程失败: {str(e)}")
            raise