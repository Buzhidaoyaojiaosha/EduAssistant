from typing import Dict, List
import random
from app.react.tools_register import register_as_tool
from app.utils.logging import logger
from app.models.course import Course
from app.models.learning_data import KnowledgePoint
import json
from app.utils.llm.deepseek import chat_deepseek
from app.services.course_service import CourseService
from app.react.tools.teaching_preparation import _get_course_knowledge_content

@register_as_tool(roles=["teacher"])
def generate_assessment_with_ai(course_id: int, num_questions: int = 10) -> List[Dict]:
    """使用AI根据课程知识库生成考核题目
    
    Args:
        course_id (int): 课程ID
        num_questions (int): 题目数量，默认为10
        
    Returns:
        List[Dict]: 生成的题目列表，包含题目内容、答案和解析
    """
    try:
        course = Course.get_by_id(course_id)
        if not course:
            return []
        
        # 获取课程知识库内容
        knowledge_content = _get_course_knowledge_content(course_id=course_id)
        
        # 构造提示词
        prompt = f"""
你是一位经验丰富的教师，需要为课程《{course.name}》设计一套考核题目。
请根据以下课程知识库内容，生成{num_questions}道题目，包含选择题、判断题、简答题和编程题：

课程知识库内容：
{knowledge_content}

要求：
1. 题目类型多样，包含选择题、判断题、简答题和编程题（当课程知识库内容涉及编程时）
2. 题目难度适中，覆盖课程核心知识点
3. 每道题包含题目内容、正确答案和详细解析
4. 返回严格的JSON格式数据，注意选择题的题目内容需要包含选项内容

返回格式示例：
{{
    "questions": [
        {{
            "type": "选择题",
            "content": "题目内容",
            "answer": "A",
            "analysis": "解析说明"
        }},
        {{
            "type": "判断题",
            "content": "题目内容",
            "answer": "对",
            "analysis": "解析说明"
        }},
        {{
            "type": "判断题",
            "content": "题目内容",
            "answer": "错",
            "analysis": "解析说明"
        }},
        {{
            "type": "简答题",
            "content": "题目内容",
            "answer": "参考答案",
            "analysis": "解析说明"
        }},
         {{
            "type": "编程题",
            "content": "题目内容",
            "answer": "参考答案",
            "analysis": "解析说明"
        }}
    ]
}}
"""
        
        messages = [
            {"role": "system", "content": "你是一位专业教师，擅长设计教学考核题目。"},
            {"role": "user", "content": prompt}
        ]
        
        # 调用DeepSeek API
        response_text = chat_deepseek(messages).strip()
        
        # 处理可能的JSON标记
        if response_text.startswith("```json") and response_text.endswith("```"):
            response_text = response_text[7:-3].strip()
        
        # 解析JSON响应
        response_data = json.loads(response_text)
        questions = response_data.get("questions", [])
        
        return questions
        
    except Exception as e:
        logger.error(f"生成考核题目失败: {str(e)}")
        return []

def generate_by_knowledge_point(knowledge_point_id: int, difficulty: str = "medium", num_questions: int = 5) -> List[Dict]:
    """根据知识点生成题目
    
    Args:
        knowledge_point_id (int): 知识点ID
        difficulty (str): 题目难度(easy/medium/hard)
        num_questions (int): 题目数量
        
    Returns:
        List[Dict]: 生成的题目列表
    """
    knowledge_point = KnowledgePoint.get_by_id(knowledge_point_id)
    if not knowledge_point:
        return []
    
    questions = []
    for i in range(num_questions):
        question_type = random.choice(["choice", "judgment", "fill", "qa", "calculation"])
        questions.append({
            "type": question_type,
            "knowledge_point": knowledge_point.name,
            "difficulty": difficulty,
            "content": _generate_question_content(question_type, knowledge_point.name),
            "answer": _generate_question_answer(question_type)
        })
    return questions

def generate_exam_paper(course_id: int, exam_type: str = "unit", 
                       question_dist: Dict = None) -> Dict:
    """生成试卷
    
    Args:
        course_id (int): 课程ID
        exam_type (str): 试卷类型(unit/final)
        question_dist (Dict): 题目分布配置
        
    Returns:
        Dict: 生成的试卷结构
    """
    course = Course.get_by_id(course_id)
    if not course:
        return {}
    
    # 默认题目分布配置
    default_dist = {
        "choice": {"count": 12, "points": 4},
        "judgment": {"count": 5, "points": 2},
        "fill": {"count": 3, "points": 2},
        "qa": {"count": 2, "points": 6},
        "calculation": {"count": 2, "points": 12}
    }
    dist = question_dist or default_dist
    
    knowledge_points = KnowledgePoint.select().where(KnowledgePoint.course == course_id)
    if not knowledge_points:
        return {}
    
    paper = {
        "title": f"{course.name} {'单元测试' if exam_type == 'unit' else '期末考试'}试卷",
        "questions": [],
        "total_points": sum(item["count"] * item["points"] for item in dist.values())
    }
    
    # 按题型生成题目
    for q_type, config in dist.items():
        for _ in range(config["count"]):
            # 轮询知识点确保均匀分布
            kp = knowledge_points[len(paper["questions"]) % len(knowledge_points)]
            paper["questions"].append({
                "type": q_type,
                "knowledge_point": kp.name,
                "difficulty": "medium",
                "content": _generate_question_content(q_type, kp.name),
                "answer": _generate_question_answer(q_type),
                "points": config["points"]
            })
    
    return paper

def _generate_question_content(question_type: str, knowledge_point: str) -> str:
    """生成题目内容"""
    if question_type == "choice":
        return f"关于{knowledge_point}的选择题: 下列哪个选项是正确的?"
    elif question_type == "judgment":
        return f"判断题: {knowledge_point}的相关描述是否正确?"
    elif question_type == "fill":
        return f"填空题: 请填写关于{knowledge_point}的关键内容: ____"
    elif question_type == "qa":
        return f"简答题: 请简述{knowledge_point}的主要内容"
    else:  # calculation
        return f"计算题: 请根据{knowledge_point}相关知识进行计算"

def _generate_question_answer(question_type: str) -> str:
    """生成题目答案"""
    if question_type == "choice":
        return "A"
    elif question_type == "judgment":
        return "正确"
    elif question_type == "fill":
        return "关键内容"
    elif question_type == "qa":
        return "这是简答题的标准答案"
    else:  # calculation
        return "42"  # 计算题答案