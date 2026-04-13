from app.react.tools.wrong_answer_analysis import get_wrong_answers, analyze_wrong_answers, provide_suggestions
from app.react.tools_register import register_as_tool
from app.react.agent import run


class WrongAnswerAnalysisService:
    """错题分析服务，处理学生错题的分析和建议。

    该服务提供错题分析相关功能，包括获取错题数据、分析错误原因和提供建议。
    """

    @register_as_tool(roles=["student", "teacher"])
    @staticmethod
    def analyze(student_id, course_id=None):
        """综合分析错题，返回分析结果和建议。

        Args:
            student_id (int): 学生用户ID
            course_id (int, optional): 课程ID，用于筛选指定课程的错题

        Returns:
            list: 包含错题分析结果和建议的列表
        """
        wrong_answers = get_wrong_answers(student_id, course_id)
        analysis_results = analyze_wrong_answers(wrong_answers)
        suggestions = provide_suggestions(analysis_results)

        return suggestions
