from app.models.base import BaseModel
from app.models.user import User
from peewee import *
import datetime

class Chat(BaseModel):
    """聊天会话模型，记录用户与AI助手的会话"""
    user = ForeignKeyField(User, backref='chats')
    title = CharField(max_length=255, default="新会话")
    is_active = BooleanField(default=True)
    
    class Meta:
        table_name = 'chats'

class ChatMessage(BaseModel):
    """聊天消息模型，记录会话中的每条消息"""
    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_SYSTEM = 'system'
    
    ROLE_CHOICES = [
        (ROLE_USER, '用户'),
        (ROLE_ASSISTANT, 'AI助手'),
        (ROLE_SYSTEM, '系统')
    ]
    
    chat = ForeignKeyField(Chat, backref='messages')
    role = CharField(max_length=20, choices=ROLE_CHOICES)
    content = TextField()
    timestamp = DateTimeField(default=datetime.datetime.now)
    
    class Meta:
        table_name = 'chat_messages'
        indexes = (
            (('chat', 'timestamp'), True),
        )
