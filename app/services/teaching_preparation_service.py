from app.react.tools.teaching_preparation import (
    generate_teaching_outline,
    generate_teaching_summary
)
from app.react.tools_register import register_as_tool
from typing import List, Dict, Optional
from peewee import DoesNotExist

class TeachingPreparationService:
    """教学准备服务，提供备课提纲和教学总结生成功能"""
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def generate_outline(course_id: int,selected_knowledge_ids: List[int] = None) -> str:
        """生成备课提纲
        
        Args:
            course_id (int): 课程ID
            week (int): 教学周次
            objectives (List[str]): 教学目标列表
            
        Returns:
            str: 生成的备课提纲
        """
        return generate_teaching_outline(course_id,selected_knowledge_ids)
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def generate_summary(course_id: int, week: int, 
                        achievements: List[str], issues: List[str]) -> str:
        """生成教学总结
        
        Args:
            course_id (int): 课程ID
            week (int): 教学周次
            achievements (List[str]): 教学成果
            issues (List[str]): 存在问题
            
        Returns:
            str: 生成的教学总结
        """
        return generate_teaching_summary(course_id, week, achievements, issues)