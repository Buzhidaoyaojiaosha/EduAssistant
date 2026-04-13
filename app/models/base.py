from playhouse.postgres_ext import Model
from peewee import *
import datetime
from app.ext import db

class BaseModel(Model):
    created_at = DateTimeField(default=datetime.datetime.now())
    updated_at = DateTimeField(default=datetime.datetime.now())
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.datetime.now()
        return super(BaseModel, self).save(*args, **kwargs)
    
    class Meta:
        database = db
