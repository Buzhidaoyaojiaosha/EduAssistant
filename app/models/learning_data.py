from peewee import CharField, TextField, ForeignKeyField, DateTimeField, FloatField, IntegerField
from playhouse.postgres_ext import JSONField
from app.models.base import BaseModel
from app.models.user import User
from app.models.course import Course
from app.models.assignment import Assignment
from app.models.knowledge_base import KnowledgeBase

class KnowledgePoint(BaseModel):
    name = CharField(max_length=100)
    description = TextField(null=True)
    course = ForeignKeyField(Course, backref='knowledge_points')
    parent = ForeignKeyField('self', backref='children', null=True)
    
    class Meta:
        indexes = (
            (('course', 'name'), True),
        )
    
    def __repr__(self):
        return f'<KnowledgePoint {self.name}>'

class StudentKnowledgePoint(BaseModel):
    student = ForeignKeyField(User, backref='knowledge_points')
    knowledge_point = ForeignKeyField(KnowledgePoint, backref='student_progress')
    mastery_level = FloatField(default=0.0)  # 0-1表示掌握程度
    last_interaction = DateTimeField(null=True)
    
    class Meta:
        indexes = (
            (('student', 'knowledge_point'), True),
        )

class LearningActivity(BaseModel):
    student = ForeignKeyField(User, backref='learning_activities')
    course = ForeignKeyField(Course, backref='learning_activities')
    knowledge_point = ForeignKeyField(KnowledgePoint, backref='learning_activities', null=True)
    activity_type = CharField(max_length=50)  # 例如：视频观看、作业完成、测验等
    duration = IntegerField(default=0)  # 活动持续时间（秒）
    timestamp = DateTimeField()
    metadata = JSONField(null=True)  # 存储额外数据，如页面访问路径、交互细节等

class AssignmentKnowledgePoint(BaseModel):
    assignment = ForeignKeyField(Assignment, backref='knowledge_points')
    knowledge_point = ForeignKeyField(KnowledgePoint, backref='related_assignments')
    weight = FloatField(default=1.0)

    class Meta:
        indexes = (
            (('assignment', 'knowledge_point'), True),
        )

class KnowledgeBaseKnowledgePoint(BaseModel):
    knowledge_base = ForeignKeyField(KnowledgeBase, backref='knowledge_points')
    knowledge_point = ForeignKeyField(KnowledgePoint, backref='related_knowledge_bases')
    weight = FloatField(default=1.0)

    class Meta:
        indexes = (
            (('knowledge_base', 'knowledge_point'), True),
        )
