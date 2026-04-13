from app.react.tools.education_copywriting import (
    generate_daily_task,
    generate_homework,
    generate_student_comment
)
from app.react.tools_register import register_as_tool
from typing import List, Dict, Optional
from peewee import DoesNotExist

class EducationCopywritingService:
    """教育文案生成服务，提供各类教育相关文案生成功能"""
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def generate_task(task_type: str, student_name: str, details: Dict) -> str:
        """生成每日任务文案
        
        Args:
            task_type (str): 任务类型
            student_name (str): 学生姓名
            details (Dict): 任务详情
            
        Returns:
            str: 生成的每日任务文案
        """
        return generate_daily_task(task_type, student_name, details)
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def generate_homework(subject: str, content: str, deadline: str) -> str:
        """生成作业布置文案
        
        Args:
            subject (str): 科目名称
            content (str): 作业内容
            deadline (str): 截止时间
            
        Returns:
            str: 生成的作业布置文案
        """
        return generate_homework(subject, content, deadline)
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def generate_comment(student_name: str, performance: Dict) -> str:
        """生成学生评语文案
        
        Args:
            student_name (str): 学生姓名
            performance (Dict): 表现评价
            
        Returns:
            str: 生成的学生评语
        """
        return generate_student_comment(student_name, performance)