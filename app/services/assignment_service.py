from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models.assignment import Assignment, StudentAssignment
from app.models.course import Course, StudentCourse
from app.models.NewAdd import Question, StudentAnswer, AIQuestion
from app.react.tools_register import register_as_tool
from peewee import DoesNotExist, fn
from app.utils.logging import logger
from app.utils.llm.deepseek import chat_deepseek
import json

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
    
    @register_as_tool(roles=["teacher", "student"])
    @staticmethod
    def get_student_answers(student_id: int, assignment_id: int) -> List[Dict[str, Any]]:
        """获取学生对特定作业的所有答案。
        
        获取指定学生对指定作业的所有题目回答，包含题目信息、学生回答内容和得分情况。
        适用于教师查看学生作业详情或进行自动评分。
        
        Args:
            student_id: 学生用户ID。
            assignment_id: 作业ID。
            
        Returns:
            包含学生答案信息的字典列表，每个答案包含以下字段：
                - submission_id (int): 提交ID
                - question_id (int): 题目ID
                - question_name (str): 题目名称
                - question_type (int): 题目类型(1:选择题, 2:判断题, 3:简答题, 其他:主观题)
                - context (str): 题目内容
                - answer (str): 正确答案
                - commit_answer (str): 学生提交的答案
                - earned_score (float): 已获得分数
                - max_score (float): 题目满分
                - analysis (str): 题目解析
                
        Raises:
            ValueError: 如果找不到相关记录。
        """
        try:
            # 验证作业存在
            assignment = Assignment.get_by_id(assignment_id)
            
            # 查询学生对该作业的所有答案
            answers = (StudentAnswer
                      .select(StudentAnswer, Question)
                      .join(Question)
                      .where(
                          (StudentAnswer.student_id == student_id) &
                          (Question.assignment_id == assignment_id)
                      ))
            
            if not answers.exists():
                return []
            
            result = []
            for answer in answers:
                result.append({
                    'submission_id': answer.submission_id,
                    'question_id': answer.question.question_id,
                    'question_name': answer.question.question_name,
                    'question_type': answer.question.status,
                    'context': answer.question.context,
                    'answer': answer.question.answer,
                    'commit_answer': answer.commit_answer,
                    'earned_score': answer.earned_score if answer.earned_score is not None else 0,
                    'max_score': answer.question.score,
                    'analysis': answer.question.analysis or ""
                })
            
            return result
        
        except DoesNotExist:
            raise ValueError(f"找不到作业ID {assignment_id} 或学生ID {student_id}")
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def auto_grade_assignment(student_id: int, assignment_id: int) -> Dict[str, Any]:
        """自动为学生作业评分。
        
        根据题目类型和预设答案自动为学生作业评分。对于客观题(选择题、判断题)完全自动评分，
        对于主观题提供初步评分建议，最终评分仍需教师确认。完成评分后更新学生作业状态。
        
        Args:
            student_id: 学生用户ID。
            assignment_id: 作业ID。
            
        Returns:
            包含评分结果的字典，包含以下字段：
                - total_score (float): 总得分
                - max_score (float): 满分
                - percentage (float): 得分百分比
                - feedback (str): 自动生成的评语
                - questions (List[Dict]): 各题目评分明细列表，每个元素包含：
                    - question_id (int): 题目ID
                    - question_name (str): 题目名称
                    - score (float): 获得分数
                    - max_score (float): 题目满分
                    - feedback (str): 题目评语
                
        Raises:
            ValueError: 如果作业不存在或尚未提交。
        """
        try:
            # 获取作业和学生提交
            assignment = Assignment.get_by_id(assignment_id)
            student_assignment = StudentAssignment.get(
                StudentAssignment.student_id == student_id,
                StudentAssignment.assignment_id == assignment_id
            )
            
            # 检查作业是否已提交
            if student_assignment.status == 0:
                raise ValueError("该作业尚未提交，无法评分")
            
            # 获取所有答案
            answers = AssignmentService.get_student_answers(student_id, assignment_id)
            
            total_score = 0
            max_score = 0
            graded_questions = []
            
            # 评分每个问题
            for answer in answers:
                question_type = answer['question_type']
                score = 0
                
                # 客观题自动评分
                if question_type in [1, 2]:  # 选择题或判断题
                    if answer['commit_answer'].strip() == answer['answer'].strip():
                        score = answer['max_score']
                        feedback = "答案正确"
                    else:
                        score = 0
                        feedback = f"答案错误，正确答案是: {answer['answer']}"
                else:
                    # 主观题建议分值(暂时给一半分)
                    score = answer['max_score'] * 0.5
                    feedback = "需要教师进一步评分"
                
                # 更新分数
                student_answer = StudentAnswer.get_by_id(answer['submission_id'])
                student_answer.earned_score = score
                student_answer.save()
                
                total_score += score
                max_score += answer['max_score']
                
                graded_questions.append({
                    'question_id': answer['question_id'],
                    'question_name': answer['question_name'],
                    'score': score,
                    'max_score': answer['max_score'],
                    'feedback': feedback
                })
            
            # 生成评语
            percentage = (total_score / max_score * 100) if max_score > 0 else 0
            if percentage >= 80:
                feedback = "表现优秀，继续保持！"
            elif percentage >= 60:
                feedback = "整体情况良好，还有进步空间。"
            else:
                feedback = "需要加强练习，建议复习相关知识点。"
            
            # 更新学生作业状态
            student_assignment.final_score = total_score
            student_assignment.feedback = feedback
            student_assignment.status = 2  # 已批改
            student_assignment.save()
            
            return {
                'total_score': total_score,
                'max_score': max_score,
                'percentage': round(percentage, 2),
                'feedback': feedback,
                'questions': graded_questions
            }
            
        except DoesNotExist:
            raise ValueError(f"找不到作业ID {assignment_id} 或学生ID {student_id} 的提交记录")
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def grade_assignment(student_id: int, assignment_id: int, score: float, feedback: str = None):
        """为学生作业评分。

        为指定的学生作业设置总分和评语，将作业状态更新为已批改。
        当教师完成作业评分后，学生将能够在系统中查看自己的成绩和反馈。

        Args:
            student_id: 学生用户ID。
            assignment_id: 作业ID。
            score: 评分分数，应为非负数值。
            feedback: 教师评语，可选。提供具体反馈以帮助学生了解自己的表现。

        Returns:
            StudentAssignment: 更新后的学生作业对象，包含最新的评分和反馈信息。

        Raises:
            DoesNotExist: 如果找不到对应的作业对象。
            ValueError: 如果分数为负数或作业尚未提交。
        """
        if score < 0:
            raise ValueError("分数不能为负数")
            
        student_assignment = StudentAssignment.get(
            StudentAssignment.student_id == student_id,
            StudentAssignment.assignment_id == assignment_id
        )
        
        if student_assignment.status == 0:
            raise ValueError("该作业尚未提交，无法评分")
            
        student_assignment.final_score = score
        student_assignment.feedback = feedback
        student_assignment.status = 2  # 已批改状态
        student_assignment.save()
        return student_assignment
    
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def grade_student_answer(submission_id: int, score: float, feedback: str = None) -> Dict[str, Any]:
        """为学生的单个题目评分。
        
        为指定的学生答案设置分数和评语，适用于教师对主观题进行单独评分。
        评分后会自动重新计算并更新学生作业的总分。
        
        Args:
            submission_id: 学生答案提交ID。
            score: 评分分数，应为非负数值。
            feedback: 针对该题的评语，可选。
            
        Returns:
            包含更新后答案信息的字典，包含以下字段：
                - submission_id (int): 提交ID
                - question_id (int): 题目ID
                - earned_score (float): 获得的分数
                - max_score (float): 题目满分
                - feedback (str): 评语
                
        Raises:
            DoesNotExist: 如果找不到对应的答案记录。
            ValueError: 如果分数为负数或超过题目满分。
        """
        if score < 0:
            raise ValueError("分数不能为负数")
            
        answer = StudentAnswer.get_by_id(submission_id)
        
        if score > answer.question.score:
            raise ValueError(f"评分 {score} 超过题目满分 {answer.question.score}")
            
        answer.earned_score = score
        answer.save()
        
        # 更新总分
        student_id = answer.student_id
        question = answer.question
        assignment_id = question.assignment_id
        
        # 重新计算总分
        total_score_query = (StudentAnswer
                           .select(fn.SUM(StudentAnswer.earned_score))
                           .join(Question)
                           .where(
                               (StudentAnswer.student_id == student_id) &
                               (Question.assignment_id == assignment_id)
                           ))
        
        total_score = total_score_query.scalar()
        
        # 更新学生作业表中的总分
        student_assignment = StudentAssignment.get(
            StudentAssignment.student_id == student_id,
            StudentAssignment.assignment_id == assignment_id
        )
        student_assignment.final_score = total_score if total_score is not None else 0
        student_assignment.save()
        
        return {
            'submission_id': answer.submission_id,
            'question_id': answer.question.question_id,
            'earned_score': answer.earned_score,
            'max_score': answer.question.score,
            'feedback': feedback
        }
    
    @register_as_tool(roles=["teacher", "student"])
    @staticmethod
    def get_assignment_statistics(assignment_id: int) -> Dict[str, Any]:
        """获取作业统计信息。
        
        获取指定作业的统计数据，包括提交情况、分数分布等信息。
        适用于教师分析作业完成情况和学生了解整体表现。
        
        Args:
            assignment_id: 作业ID。
            
        Returns:
            包含作业统计信息的字典，包含以下字段：
                - assignment_id (int): 作业ID
                - assignment_title (str): 作业标题
                - total_students (int): 总学生数
                - submitted_count (int): 已提交数量
                - graded_count (int): 已批改数量
                - submission_rate (float): 提交率百分比
                - average_score (float): 平均分
                - max_score (float): 最高分
                - min_score (float): 最低分
                - score_distribution (Dict): 分数段分布
                
        Raises:
            ValueError: 如果作业不存在。
        """
        try:
            assignment = Assignment.get_by_id(assignment_id)
            
            # 获取所有学生作业记录
            submissions = StudentAssignment.select().where(
                StudentAssignment.assignment_id == assignment_id
            )
            
            total_students = submissions.count()
            submitted_count = submissions.where(StudentAssignment.status >= 1).count()
            graded_count = submissions.where(StudentAssignment.status == 2).count()
            
            # 计算提交率
            submission_rate = (submitted_count / total_students * 100) if total_students > 0 else 0
            
            # 获取已批改作业的分数统计
            graded_submissions = submissions.where(
                (StudentAssignment.status == 2) & 
                (StudentAssignment.final_score.is_null(False))
            )
            
            scores = [s.final_score for s in graded_submissions if s.final_score is not None]
            
            if scores:
                average_score = sum(scores) / len(scores)
                max_score = max(scores)
                min_score = min(scores)
                
                # 分数段分布（优秀、良好、及格、不及格）
                total_points = assignment.total_points
                excellent = sum(1 for s in scores if s >= total_points * 0.9)
                good = sum(1 for s in scores if total_points * 0.8 <= s < total_points * 0.9)
                pass_score = sum(1 for s in scores if total_points * 0.6 <= s < total_points * 0.8)
                fail = sum(1 for s in scores if s < total_points * 0.6)
                
                score_distribution = {
                    'excellent': excellent,
                    'good': good,
                    'pass': pass_score,
                    'fail': fail
                }
            else:
                average_score = 0
                max_score = 0
                min_score = 0
                score_distribution = {'excellent': 0, 'good': 0, 'pass': 0, 'fail': 0}
            
            return {
                'assignment_id': assignment_id,
                'assignment_title': assignment.title,
                'total_students': total_students,
                'submitted_count': submitted_count,
                'graded_count': graded_count,
                'submission_rate': round(submission_rate, 2),
                'average_score': round(average_score, 2) if scores else 0,
                'max_score': max_score,
                'min_score': min_score,
                'score_distribution': score_distribution
            }
            
        except DoesNotExist:
            raise ValueError(f"作业ID {assignment_id} 不存在")

    @staticmethod
    def update_assignment_total_points(assignment_id):
        """根据题目分值更新作业的总分。
        
        Args:
            assignment_id (int): 作业ID
            
        Returns:
            float: 更新后的总分
        """
        from app.models.NewAdd import Question
        from app.models.assignment import Assignment
        
        # 获取作业的所有题目
        questions = Question.select().where(Question.assignment_id == assignment_id)
        
        # 计算总分
        total_points = sum(q.score for q in questions)
        
        # 更新作业总分
        assignment = Assignment.get_by_id(assignment_id)
        assignment.total_points = total_points
        assignment.save()
        
        return total_points

    @staticmethod
    def grade_short_answer_with_deepseek(question: str, student_answer: str, max_score: float, model="deepseek-chat") -> float:
        """使用DeepSeek API对简答题进行自动评分
        
        Args:
            question (str): 题目内容
            student_answer (str): 学生答案
            max_score (float): 该题最高分值
            model (str): 使用的模型名称，默认为deepseek-chat
            
        Returns:
            float: 评分结果(0到max_score之间)
            
        Raises:
            ValueError: 如果API调用失败或返回无效结果
        """
        try:
            # 构造评分提示词
            prompt = f"""
            请根据以下题目和参考答案，对学生的答案进行评分。
            评分标准应基于答案的准确性、完整性和相关性。
            
            题目: {question}
            参考答案: 请根据题目内容自行判断
            学生答案: {student_answer}
            
            请按照以下要求评分:
            1. 评分范围: 0-{max_score}分
            2. 给出具体评分(只能是数字)
            3. 简要说明评分理由(50字以内)
            
            返回格式必须严格遵循:
            评分: [分数]
            理由: [评分理由]
            """
            
            messages = [
                {"role": "system", "content": "你是一个专业的教学助理，负责对学生的简答题答案进行评分。"},
                {"role": "user", "content": prompt}
            ]
            
            # 调用DeepSeek API
            response_text = chat_deepseek(messages)
            if not response_text:
                raise ValueError("DeepSeek API返回空响应")
            
            # 解析API响应
            score_line = next((line for line in response_text.split('\n') if line.startswith('评分:')), None)
            if not score_line:
                raise ValueError("无法从响应中解析评分")
            
            try:
                score = float(score_line.split(':')[1].strip())
            except (IndexError, ValueError):
                raise ValueError("评分格式无效")
                
            # 确保分数在合理范围内
            score = max(0, min(max_score, score))
            
            logger.info(f"简答题评分完成 - 题目: {question[:50]}... | 得分: {score}/{max_score}")
            return score
            
        except Exception as e:
            logger.error(f"简答题自动评分失败: {str(e)}")
            raise ValueError(f"自动评分失败: {str(e)}")
 

    @staticmethod
    def generate_feedback_with_deepseek(student_answers: list, total_score: float, max_score: float) -> str:
        """使用DeepSeek API生成总体评语
        
        Args:
            student_answers: 学生答案列表（包含题目和得分信息）
            total_score: 学生获得的总分
            max_score: 作业总分
            
        Returns:
            str: 生成的评语内容
        """
        try:
            # 构造提示词
            prompt = f"""
            你是一位经验丰富的教师，需要为学生的作业撰写总体评语。
            
            作业情况：
            - 总分：{total_score}/{max_score}
            - 各题得分情况：
            {chr(10).join(f"题目 {i+1}: {ans['question'][:50]}... | 得分: {ans['score']}/{ans['max_score']}" for i, ans in enumerate(student_answers))}
            
            请根据以下要求撰写评语：
            1. 首先指出整体表现
            2. 分析优点和需要改进的地方
            3. 给出具体的学习建议
            4. 语言简洁专业，200字左右
            5. 使用中文
            
            评语格式：
            【整体评价】...
            【优点】...
            【改进建议】...
            """
            
            messages = [
                {"role": "system", "content": "你是一位专业教师，擅长撰写作业评语。"},
                {"role": "user", "content": prompt}
            ]
            
            # 调用DeepSeek API
            response_text = chat_deepseek(messages)
            if not response_text:
                raise ValueError("DeepSeek API返回空响应")
            
            return response_text.strip()
            
        except Exception as e:
            logger.error(f"生成评语失败: {str(e)}")
            # 返回默认评语
            return f"""【整体评价】作业已完成，获得{total_score}/{max_score}分。
            【优点】完成了所有题目。
            【改进建议】请继续努力，加强对知识点的理解。"""


    def get_question_type_name(status: int) -> str:
        """获取题目类型名称"""
        types = {
            1: "选择题",
            2: "判断题",
            3: "简答题"
        }
        return types.get(status, "未知类型")


    def extract_questions_from_text(text: str) -> list:
        """从非结构化文本中提取题目信息"""
        # 这里实现一个简单的文本解析逻辑，实际应用中可能需要更复杂的处理
        questions = []
        parts = text.split("\n\n")  # 假设每个题目之间有两个换行
        
        for part in parts:
            if not part.strip():
                continue
                
            # 简单解析各部分
            lines = [line.strip() for line in part.split("\n") if line.strip()]
            if len(lines) < 3:  # 至少包含题目、答案和解析
                continue
                
            question_data = {
                "question_name": "AI生成题目",
                "context": lines[0].replace("题目:", "").strip(),
                "answer": lines[1].replace("答案:", "").strip(),
                "analysis": lines[2].replace("解析:", "").strip(),
                "status": 3  # 默认简答题
            }
            print(f"extractquestionsfromtext提取题目: {question_data['context']}\n答案: {question_data['answer']}\n解析: {question_data['analysis']}")
            questions.append(question_data)
            
        return questions

    def generate_similar_questions_with_ai(original_question: Question, assignment: Assignment, num_questions: int = 3) -> list:
        """使用AI生成与原始题目相似的题目"""
        try:
            # 1. 构造更明确的提示词，要求AI返回严格JSON格式
            prompt = f"""
            请严格按以下JSON格式生成{num_questions}道与原始题目相似的题目：
            {{
                "questions": [
                    {{
                        "question_name": "题目名称（与原始题目知识点相关）",
                        "context": "题目内容（考察点相同但表述不同）",
                        "answer": "答案",
                        "analysis": "解析（解释为什么是这个答案）",
                        "status": {original_question.status}  # 保持与原题一致
                    }}
                ]
            }}

            原始题目参考：
            - 类型: {AssignmentService.get_question_type_name(original_question.status)}
            - 内容: {original_question.context}
            - 答案: {original_question.answer}
            - 解析: {original_question.analysis}
            """
            
            messages = [
                {"role": "system", "content": "你必须严格返回合法的JSON格式数据，仅包含题目信息，不要额外解释。"},
                {"role": "user", "content": prompt}
            ]
            
            # 2. 调用API并验证响应
            response_text = chat_deepseek(messages).strip()
            if not response_text:
                raise ValueError("API返回空响应")

            # 3. 处理可能存在的JSON外围标记（如```json```）
            if response_text.startswith("```json") and response_text.endswith("```"):
                response_text = response_text[7:-3].strip()
            
            # 4. 安全解析JSON
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败，原始响应: {response_text}")
                raise ValueError(f"API返回了非JSON数据: {e}")

            # 5. 数据校验
            generated_questions_data = response_data.get("questions", [])
            if not isinstance(generated_questions_data, list):
                raise ValueError("questions字段必须是列表")

            # 6. 保存题目（添加字段缺失处理）
            generated_questions = []
            for q_data in generated_questions_data[:num_questions]:
                try:
                    ai_question = AIQuestion.create(
                        original_question=original_question,
                        question_name=q_data.get("question_name", "AI生成题目"),
                        assignment=assignment,
                        course=assignment.course,
                        context=q_data["context"],  # 必需字段，若无则抛异常
                        answer=q_data["answer"],
                        analysis=q_data.get("analysis", "无解析"),
                        status=q_data.get("status", original_question.status),
                        is_approved=False
                    )
                    generated_questions.append(ai_question)
                except KeyError as e:
                    logger.warning(f"跳过无效题目：缺少必要字段 {e}")
                    continue

            return generated_questions

        except Exception as e:
            logger.error(f"生成相似题目失败: {str(e)}", exc_info=True)
            raise  # 根据业务需求决定是否重新抛出异常