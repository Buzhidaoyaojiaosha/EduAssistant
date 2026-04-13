from peewee import *
from datetime import datetime
from app.models.base import BaseModel
from app.models.user import User
from app.models.course import Course
from app.models.assignment import Assignment

class Question(BaseModel):
    question_id = AutoField(primary_key=True)  # 修改为自增主键
    question_name = CharField(max_length=255)
    assignment = ForeignKeyField(Assignment, backref='questions')
    course = ForeignKeyField(Course, backref='questions')
    context = TextField(null=False)
    answer = TextField(null=False)
    analysis = TextField()
    score = FloatField()
    status = IntegerField()  #  1:选择题, 2:判断题, 3:简答题
    created_time = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'question'



class AIQuestion(BaseModel):
    ai_question_id = AutoField(primary_key=True)  # AI生成题目的唯一ID
    original_question = ForeignKeyField(Question, backref='ai_generated_questions')  # 关联原始题目
    question_name = CharField(max_length=255)  # 题目名称
    assignment = ForeignKeyField(Assignment, backref='ai_questions')  # 关联作业
    course = ForeignKeyField(Course, backref='ai_questions')  # 关联课程
    context = TextField(null=False)  # 题目内容
    answer = TextField(null=False)  # 答案
    analysis = TextField(null=False, default='暂无解析')  # 非空且有默认值
    status = IntegerField()  # 题目类型: 1:选择题, 2:判断题, 3:简答题,4:编程题
    created_time = DateTimeField(default=datetime.now)  # 创建时间
    is_approved = BooleanField(default=False)  # 是否已被老师审核通过 false表示未加入题库，true表示加入题库


    class Meta:
        table_name = 'aiquestion'

class AiQuestionStudentAnswer(BaseModel):
    ai_submission_id = AutoField(primary_key=True)  # 自增主键
    student = ForeignKeyField(User, backref='ai_answers')  # 关联学生用户
    ai_question = ForeignKeyField(AIQuestion, backref='student_answers')  # 关联AI生成的题目
    student_answer = TextField()  # 学生提交的答案
    ai_feedback = TextField()  # AI生成的纠错评语
    submission_time = DateTimeField(default=datetime.now)
    class Meta:
        table_name = 'aiquestionstudentanswer'

class StudentAnswer(BaseModel):
    submission_id = AutoField(primary_key=True)  # 修改为自增主键
    student = ForeignKeyField(User, backref='answers')
    question = ForeignKeyField(Question, backref='student_answers')
    commit_answer = TextField()
    earned_score = FloatField()
    work_time = DateTimeField(default=datetime.now)
    answerImagePath = CharField(max_length=255, null=True)  # 添加图片路径字段，允许为空

    class Meta:
        table_name = 'studentanswer'

class Feedback(BaseModel):
    feedback_id = AutoField(primary_key=True)  # 修改为自增主键
    assignment = ForeignKeyField(Assignment, backref='feedbacks')
    student = ForeignKeyField(User, backref='feedbacks')
    comment = TextField()
    created_time = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'feedback'

class WrongBook(BaseModel):
    wrong_book_id = AutoField(primary_key=True)  # 修改为自增主键
    wrong_book_name = CharField(max_length=255)
    student = ForeignKeyField(User, backref='wrong_books')
    course = ForeignKeyField(Course, backref='wrong_books')
    created_time = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'wrongbook'

class QuestionWrongBook(BaseModel):
    question_wrong_book_id = AutoField(primary_key=True)  # 修改为自增主键
    wrong_book = ForeignKeyField(WrongBook, backref='question_wrong_books')
    question = ForeignKeyField(Question, backref='wrong_books')
    created_time = DateTimeField(default=datetime.now)
    student_answer = ForeignKeyField(StudentAnswer, backref='question_wrong')

    class Meta:
        table_name = 'questionwrongbook'