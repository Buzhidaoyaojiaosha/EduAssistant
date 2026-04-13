from peewee import CharField, BooleanField, ForeignKeyField
from app.models.base import BaseModel, db

class User(BaseModel):
    username = CharField(max_length=80, unique=True)
    email = CharField(max_length=120, unique=True)
    password_hash = CharField(max_length=255)
    name = CharField(max_length=100)
    is_active = BooleanField(default=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Role(BaseModel):
    name = CharField(max_length=80, unique=True)
    description = CharField(max_length=255)
    
    def __repr__(self):
        return f'<Role {self.name}>'

class UserRole(BaseModel):
    user = ForeignKeyField(User, backref='roles')
    role = ForeignKeyField(Role, backref='users')
    
    class Meta:
        indexes = (
            (('user', 'role'), True),  # 确保用户-角色组合唯一
        )
