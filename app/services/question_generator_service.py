from app.react.tools.question_generator import (
    generate_by_knowledge_point,
    generate_exam_paper
)
from app.react.tools_register import register_as_tool
from typing import List, Dict, Optional
from peewee import DoesNotExist

class QuestionGeneratorService:
    """题目生成服务，提供按知识点和课程生成题目的功能"""
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def generate_questions(knowledge_point_id: int, difficulty: str = "medium", num_questions: int = 5) -> List[Dict]:
        """根据知识点生成题目
        
        Args:
            knowledge_point_id (int): 知识点ID
            difficulty (str): 题目难度
            num_questions (int): 题目数量
            
        Returns:
            List[Dict]: 生成的题目列表
        """
        return generate_by_knowledge_point(knowledge_point_id, difficulty, num_questions)
    
    @register_as_tool(roles=["student","teacher"])
    @staticmethod
    def generate_exam(course_id: int, exam_type: str = "unit") -> Dict:
        """生成试卷
        
        Args:
            course_id (int): 课程ID
            exam_type (str): 试卷类型
            
        Returns:
            Dict: 生成的试卷结构
        """
        return generate_exam_paper(course_id, exam_type)