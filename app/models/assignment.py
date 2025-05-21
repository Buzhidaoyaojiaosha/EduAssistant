from peewee import *
from app.models.base import BaseModel
from app.models.course import Course
from app.models.user import User

class Assignment(BaseModel):
    title = CharField(max_length=100)
    description = TextField()
    course = ForeignKeyField(Course, backref='assignments')
    due_date = DateTimeField()
    total_points = FloatField(default=100.0)
    
    def __repr__(self):
        return f'<Assignment {self.title} for {self.course.code}>'

class StudentAssignment(BaseModel):
    assignment = ForeignKeyField(Assignment, backref='student_assignments')
    student = ForeignKeyField(User, backref='assignments')
    course = ForeignKeyField(Course, backref='student_assignments', null=True)
    status = IntegerField(default=0)  # 0:未提交, 1:已提交, 2:已批改
    total_score = FloatField(null=True)  # 总分
    final_score = FloatField(null=True)  # 最终得分
    work_time = DateTimeField(null=True)  # 提交时间
    
    
    class Meta:
        primary_key = CompositeKey('assignment', 'student')
        table_name = 'studentassignment'
