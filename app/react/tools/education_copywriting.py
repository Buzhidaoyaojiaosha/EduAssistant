from typing import Dict, List
from datetime import datetime
from app.react.tools_register import register_as_tool
from app.utils.logging import logger

def generate_daily_task(task_type: str, student_name: str, details: Dict) -> str:
    """生成每日任务文案
    
    Args:
        task_type (str): 任务类型(跳绳/阅读等)
        student_name (str): 学生姓名
        details (Dict): 任务详情
        
    Returns:
        str: 生成的每日任务文案
    """
    if task_type == "跳绳":
        return f"{student_name}同学，今日跳绳任务：\n" \
               f"- 目标次数：{details.get('target', 100)}次\n" \
               f"- 完成时间：{details.get('time', '18:00前')}\n" \
               "请按时完成并拍照打卡！"
    elif task_type == "阅读":
        return f"{student_name}同学，今日阅读任务：\n" \
               f"- 书目：《{details.get('book', '未指定')}》\n" \
               f"- 阅读时长：{details.get('duration', '30分钟')}\n" \
               "请家长监督完成并签字确认。"

def generate_homework(subject: str, content: str, deadline: str) -> str:
    """生成作业布置文案
    
    Args:
        subject (str): 科目名称
        content (str): 作业内容
        deadline (str): 截止时间
        
    Returns:
        str: 生成的作业布置文案
    """
    return f"【{subject}作业布置】\n" \
           f"内容：{content}\n" \
           f"截止时间：{deadline}\n" \
           "请同学们按时完成，家长签字后提交。"

def generate_student_comment(student_name: str, performance: Dict) -> str:
    """生成学生评语文案
    
    Args:
        student_name (str): 学生姓名
        performance (Dict): 表现评价
        
    Returns:
        str: 生成的学生评语
    """
    strengths = "、".join(performance.get('strengths', [])) or "无"
    improvements = "、".join(performance.get('improvements', [])) or "无"
    
    return f"{student_name}同学本学期表现：\n" \
           f"优点：{strengths}\n" \
           f"待改进：{improvements}\n" \
           f"综合评语：{performance.get('summary', '继续努力')}"