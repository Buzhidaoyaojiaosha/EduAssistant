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
    status = IntegerField()  #  1:选择题, 2:判断题, 3:填空题,others主观题,
    created_time = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'question'

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