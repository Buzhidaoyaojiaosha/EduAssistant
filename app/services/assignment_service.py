from datetime import datetime
from typing import Optional
from app.models.assignment import Assignment, StudentAssignment
from app.models.course import Course, StudentCourse
from app.react.tools_register import register_as_tool
from peewee import DoesNotExist

class AssignmentService:
    """作业服务类，处理作业管理和学生作业提交。
    
    该服务提供作业相关的所有功能，包括作业创建、分发、提交、
    评分等功能。
    """
    
    @staticmethod
    def create_assignment(title, description, course_id, due_date, total_points=100.0):
        """创建新作业。
        
        Args:
            title (str): 作业标题
            description (str): 作业描述
            course_id (int): 课程ID
            due_date (datetime): 截止日期
            total_points (float): 总分，默认为100
            
        Returns:
            Assignment: 创建的作业对象
        """
        course = Course.get_by_id(course_id)
        return Assignment.create(
            title=title,
            description=description,
            course=course,
            due_date=due_date,
            total_points=total_points
        )
    
    @staticmethod
    def get_assignment_by_id(assignment_id):
        """获取作业详情
        Args:
            assignment_id (int): Assignment对象ID

        Returns:
            Assignment: 作业对象

        Raises:
            DoesNotExist: 如果作业不存在
        """
        return Assignment.get_by_id(assignment_id)
    
    @staticmethod
    def assign_to_students(assignment_id):
        """将作业分配给所有选课学生。
        
        Args:
            assignment_id (int): 作业ID
            
        Returns:
            int: 分配的学生作业数量
        """
        assignment = Assignment.get_by_id(assignment_id)
        students = StudentCourse.select().where(StudentCourse.course == assignment.course)
        
        # 批量创建学生作业记录
        created = 0
        for student_course in students:
            if not StudentAssignment.select().where(
                (StudentAssignment.student == student_course.student) &
                (StudentAssignment.assignment == assignment)
            ).exists():
                StudentAssignment.create(
                    student=student_course.student,
                    assignment=assignment
                )
                created += 1
        
        return created
    
    @staticmethod
    def submit_assignment(student_id, assignment_id, answer):
        """提交或评分作业。
        
        Args:
            student_id (int): 学生用户ID
            assignment_id (int): 作业ID
            score (float, optional): 分数，如果提供则表示评分
            
        Returns:
            StudentAssignment: 更新后的学生作业对象
            
        """
        #student_assignment = StudentAssignment.get_or_none(
        
        assignment = Assignment.get_by_id(assignment_id)
        enrollment = StudentCourse.select().where(
            (StudentCourse.student == student_id) &
            (StudentCourse.course == assignment.course)
        ).get_or_none()

        if not enrollment:
            raise ValueError("学生未加入课程")

        student = enrollment.student
        student_assignment, created = StudentAssignment.get_or_create(
            student = student,
            assignment = assignment
        )
        
        #if not student_assignment:
        #    raise ValueError("无法找到对应的学生作业记录")
        
        student_assignment.answer = answer
        student_assignment.work_time = datetime.now()
        #student_assignment.attempts += 1
        student_assignment.status = 1
            
        student_assignment.save()
        return student_assignment
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def grade_assignment(student_id: int, assignment_id: int, score: float, feedback: str = Optional[str]):
        """为作业评分

        Args:
            assignment_id (int): Assignment对象ID
            score (float): 评分
            feedback: 反馈
        
        Returns:
            StudentAssignment: 更新后的学生作业对象

        Raises:
            DoesNotExist: 如果找不到对应的作业对象
        """
        student_assignment = StudentAssignment.get(
            StudentAssignment.student==student_id,
            StudentAssignment.assignment==assignment_id
        )
        student_assignment.score = score
        student_assignment.feedback = feedback
        #student_assignment.completed = True
        student_assignment.status = 2
        student_assignment.save()
        return student_assignment
    
    @register_as_tool(roles=["student", "teacher"])
    @staticmethod
    def get_student_assignments(student_id, course_id=None,completed=None):
        """
        获取学生的作业列表，可以按课程和完成状态筛选
        
        Args:
            student_id (int): 学生ID
            course_id (int, optional): 课程ID，用于筛选
            
        Returns:
            list: StudentAssignment对象列表
        """
        query = (StudentAssignment
                 .select(StudentAssignment, Assignment, Course)
                 .join(Assignment)
                 .join(Course, on=(Assignment.course_id == Course.id))
                 .where(StudentAssignment.student_id == student_id))
        
        if course_id:
            query = query.where(Assignment.course_id == course_id)
            
        
        if completed is not None:
            if completed:
                # 状态大于0表示作业已提交（不是"待完成"）
                query = query.where(StudentAssignment.status > 0)
            else:
                # 状态为0表示作业待完成
                query = query.where(StudentAssignment.status == 0)
        
        return list(query)
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def get_course_assignments(course_id):
        """获取课程的所有作业。
        
        Args:
            course_id (int): 课程ID
            
        Returns:
            list: 作业对象列表
        """
        return list(Assignment.select().where(Assignment.course_id == course_id))

    
