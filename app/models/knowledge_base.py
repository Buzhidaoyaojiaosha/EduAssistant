from peewee import *
from playhouse.postgres_ext import JSONField
from app.models.base import BaseModel
from app.models.course import Course

class KnowledgeBase(BaseModel):
    title = CharField(max_length=200)
    type = TextField()  # 知识库条目的类型，1:纯文字，2：pdf,3:pptx,4:其他
    content = TextField()
    course = ForeignKeyField(Course, backref='knowledge_base', null=True)
    category = CharField(max_length=100, null=True)
    tags = JSONField(null=True)  # 存储标签列表
    vector_id = CharField(max_length=100, null=True)  # 在Chroma中的向量ID
    is_chunk = BooleanField(default=False)  # 标记是否为切分片段
    chunk_index = IntegerField(null=True)  # 切分片段的下标
    # source_file = TextField(null=True)  # 源文件链接

    
    def __repr__(self):
        return f'<KnowledgeBase {self.title}>'
