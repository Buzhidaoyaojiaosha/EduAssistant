from peewee import *
from datetime import datetime
from app.models.base import BaseModel
from app.models.user import User
from app.models.course import Course

class TeachingActivity(BaseModel):
    teacher = ForeignKeyField(User, backref='teaching_activities')
    course = ForeignKeyField(Course, backref='teaching_activities')
    activity_type = CharField(max_length=50)  # 如：讲课、批改作业、答疑、教研等
    duration = IntegerField(default=0)        # 活动持续时间（秒）
    timestamp = DateTimeField(default=datetime.now)
    metadata = TextField(null=True)           # 可存储JSON字符串
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'teachingactivity'