import pandas as pd
from datetime import datetime, timedelta

from sympy.physics.units import days

from app.models.learning_data import LearningActivity, StudentKnowledgePoint, KnowledgePoint
from app.models.assignment import StudentAssignment, Assignment
from app.models.course import Course
from app.models.user import User
from app.models.teaching_data import TeachingActivity
from app.react.tools_register import register_as_tool

class AnalyticsService:
    """学习数据分析服务，处理学习行为数据分析和学习情况评估。
    
    该服务提供数据分析相关功能，包括学习行为记录、知识点掌握度评估、
    学习预警和学习趋势分析等。
    """
    
    @staticmethod
    def record_learning_activity(student_id, course_id, activity_type, 
                                duration=0, knowledge_point_id=None, metadata=None):
        """记录学习活动。
        
        Args:
            student_id (int): 学生用户ID
            course_id (int): 课程ID
            activity_type (str): 活动类型
            duration (int): 持续时间（秒）
            knowledge_point_id (int, optional): 知识点ID
            metadata (dict, optional): 额外元数据
            
        Returns:
            LearningActivity: 创建的学习活动记录
        """
        leanring_activity = LearningActivity.create(
            student_id=student_id,
            course_id=course_id,
            activity_type=activity_type,
            duration=duration,
            knowledge_point_id=knowledge_point_id,
            timestamp=datetime.now(),
            metadata=metadata
        )
        leanring_activity.save()
        return leanring_activity
    
    @staticmethod
    def update_knowledge_mastery(student_id, knowledge_point_id, score_change):
        """更新知识点掌握度。
        
        Args:
            student_id (int): 学生用户ID
            knowledge_point_id (int): 知识点ID
            score_change (float): 分数变化（可正可负）
            
        Returns:
            StudentKnowledgePoint: 更新后的学生知识点对象
        """
        record, created = StudentKnowledgePoint.get_or_create(
            student_id=student_id,
            knowledge_point_id=knowledge_point_id,
            defaults={'mastery_level': 0.0}
        )
        
        # 更新掌握度，确保在0-1范围内
        new_level = record.mastery_level + score_change
        record.mastery_level = max(0.0, min(1.0, new_level))
        record.last_interaction = datetime.now()
        record.save()
        
        return record
    
    @register_as_tool(roles=["student", "teacher"])
    @staticmethod
    def get_student_knowledge_mastery(student_id, course_id=None):
        """获取学生知识点掌握情况。
        
        Args:
            student_id (int): 学生用户ID
            course_id (int, optional): 课程ID，用于筛选指定课程的知识点
            
        Returns:
            dict: 以知识点ID为键，掌握度为值的字典
        """
        query = StudentKnowledgePoint.select().where(StudentKnowledgePoint.student_id == student_id)
        
        if course_id:
            query = query.join(KnowledgePoint).where(KnowledgePoint.course_id == course_id)
            
        results = {}
        for record in query:
            results[record.knowledge_point_id] = {
                'mastery_level': record.mastery_level,
                'last_interaction': record.last_interaction,
                'knowledge_point_name': record.knowledge_point.name
            }
            
        return results
    
    @register_as_tool(roles=["student", "teacher"])
    @staticmethod
    def get_student_activity_summary(student_id, course_id=None, days=360):
        """获取学生活动概要。
        
        Args:
            student_id (int): 学生用户ID
            course_id (int, optional): 课程ID
            days (int): 统计天数，默认30天
            
        Returns:
            dict: 包含活动统计信息的字典
        """
        start_date = datetime.now() - timedelta(days=days)
        
        query = LearningActivity.select().where(
            (LearningActivity.student_id == student_id) &
            (LearningActivity.timestamp >= start_date)
        )
        
        if course_id:
            query = query.where(LearningActivity.course_id == course_id)
            
        activities = list(query)
        
        if not activities:
            return {
                'total_activities': 0,
                'total_duration': 0,
                'activity_types': {},
                'daily_activities': {}
            }
            
        # 将活动数据转换为DataFrame以便于分析
        df = pd.DataFrame([{
            'timestamp': a.timestamp,
            'activity_type': a.activity_type,
            'duration': a.duration
        } for a in activities])
        
        # 按活动类型统计
        activity_types = df.groupby('activity_type').agg({
            'activity_type': 'count',
            'duration': 'sum'
        }).rename(columns={'activity_type': 'count'}).to_dict('index')
        
        # 按日期统计
        df['date'] = df['timestamp'].dt.date
        daily_activities = df.groupby('date').agg({
            'timestamp': 'count',
            'duration': 'sum'
        }).rename(columns={'timestamp': 'count'}).to_dict('index')
        
        # 转换日期格式为字符串以便JSON序列化
        daily_activities = {str(k): v for k, v in daily_activities.items()}
        
        return {
            'total_activities': len(activities),
            'total_duration': df['duration'].sum(),
            'activity_types': activity_types,
            'daily_activities': daily_activities
        }
    
    @register_as_tool(roles=["student", "teacher"])
    @staticmethod
    def detect_learning_issues(student_id, course_id=None, threshold=0.5):
        """检测学习问题，包括低活跃度、低掌握度等。
        
        Args:
            student_id (int): 学生用户ID
            course_id (int, optional): 课程ID
            threshold (float): 掌握度阈值，低于此值视为问题
            
        Returns:
            dict: 检测到的问题列表
        """
        issues = []
        
        # 检查低掌握度知识点
        mastery_data = AnalyticsService.get_student_knowledge_mastery(student_id, course_id)
        low_mastery_points = [
            {'id': point_id, 'name': data['knowledge_point_name'], 'level': data['mastery_level']}
            for point_id, data in mastery_data.items()
            if data['mastery_level'] < threshold
        ]
        
        if low_mastery_points:
            issues.append({
                'type': 'low_mastery',
                'message': f'发现{len(low_mastery_points)}个掌握度较低的知识点',
                'details': low_mastery_points
            })
        
        # 检查未提交作业
        overdue_assignments = []
        now = datetime.now()
        
        query = StudentAssignment.select().join(Assignment)
        query = query.where(
            (StudentAssignment.student_id == student_id) &
            # 修改这里：使用status字段代替completed字段
            # status为0表示作业待完成（未提交）
            (StudentAssignment.status == 0) &
            (Assignment.due_date < now)
        )
        
        if course_id:
            query = query.where(Assignment.course_id == course_id)
            
        for sa in query:
            overdue_assignments.append({
                'id': sa.assignment_id,
                'title': sa.assignment.title,
                'due_date': str(sa.assignment.due_date)
            })
            
        if overdue_assignments:
            issues.append({
                'type': 'overdue_assignments',
                'message': f'发现{len(overdue_assignments)}个已过期未提交的作业',
                'details': overdue_assignments
            })
            
        # 检查低活跃度
        activity_summary = AnalyticsService.get_student_activity_summary(student_id, course_id, days=7)
        if activity_summary['total_activities'] == 0:
            issues.append({
                'type': 'inactive',
                'message': '过去7天内无学习活动记录',
                'details': None
            })
            
        return {
            'has_issues': len(issues) > 0,
            'issues': issues
        }

    @staticmethod
    def get_all_student_activity():
        """获取所有学生的日、周活跃度（次数），基于updated_at字段"""
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        week_start = now - timedelta(days=7)

        # 查询所有学生ID
        student_ids = (LearningActivity
                       .select(LearningActivity.student_id)
                       .distinct())

        result = {}
        for sid_obj in student_ids:
            sid = sid_obj.student_id
            # 今日活跃度（次数），基于updated_at
            today_count = (LearningActivity
                           .select()
                           .where(
                               (LearningActivity.student_id == sid) &
                               (LearningActivity.updated_at >= today_start)
                           )
                           .count())
            # 近一周活跃度（次数），基于updated_at
            week_count = (LearningActivity
                          .select()
                          .where(
                              (LearningActivity.student_id == sid) &
                              (LearningActivity.updated_at >= week_start)
                          )
                          .count())
            result[sid] = {
                "daily": today_count,
                "weekly": week_count
            }
        
        return result 
        
    @staticmethod
    def get_all_teacher_activity():
        """获取所有教师的日、周活跃度（次数），基于TeachingActivity表的updated_at字段"""
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        week_start = now - timedelta(days=7)

        # 查询所有教师ID
        teacher_ids = (TeachingActivity
                       .select(TeachingActivity.teacher_id)
                       .distinct())

        result = {}
        for tid_obj in teacher_ids:
            tid = tid_obj.teacher_id
            # 今日活跃度（次数），基于updated_at
            today_count = (TeachingActivity
                           .select()
                           .where(
                               (TeachingActivity.teacher_id == tid) &
                               (TeachingActivity.timestamp >= today_start)
                           )
                           .count())
            # 近一周活跃度（次数），基于updated_at
            week_count = (TeachingActivity
                          .select()
                          .where(
                              (TeachingActivity.teacher_id == tid) &
                              (TeachingActivity.timestamp >= week_start)
                          )
                          .count())
            result[tid] = {
                "daily": today_count,
                "weekly": week_count
            }
        return result