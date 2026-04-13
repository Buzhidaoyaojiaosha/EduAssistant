from peewee import CharField, TextField, ForeignKeyField, BooleanField
from app.models.base import BaseModel
from app.models.user import User

class Course(BaseModel):
    name = CharField(max_length=100)
    code = CharField(max_length=20, unique=True)
    description = TextField(null=True)
    teacher = ForeignKeyField(User, backref='taught_courses')
    is_active = BooleanField(default=True)
    
    def __repr__(self):
        return f'<Course {self.code}: {self.name}>'

class StudentCourse(BaseModel):
    student = ForeignKeyField(User, backref='enrolled_courses')
    course = ForeignKeyField(Course, backref='students')
    is_active = BooleanField(default=True)
    
    class Meta:
        indexes = (
            (('student', 'course'), True),  # 确保学生-课程组合唯一
        )
