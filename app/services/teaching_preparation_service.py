from app.react.tools.teaching_preparation import (
    generate_teaching_material,
    save_teaching_material_to_kb
)
from app.react.tools_register import register_as_tool
from typing import List, Dict, Optional
from peewee import DoesNotExist

class TeachingPreparationService:
    """教学准备服务，提供备课提纲生成功能"""
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def generate_outline(course_id: int,material_type:str,selected_knowledge_ids: List[int] = None) -> str:
        """生成备课提纲
        
        Args:
            course_id (int): 课程ID
            week (int): 教学周次
            objectives (List[str]): 教学目标列表
            
        Returns:
            str: 生成的备课提纲
        """
        return generate_teaching_material(course_id,material_type,selected_knowledge_ids)
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def save_teaching_material(course_id: int, title: str, file_base64: str, filename: str) -> Dict:
        """保存备课资料至知识库"""
        return save_teaching_material_to_kb(course_id,title,file_base64,filename)
    