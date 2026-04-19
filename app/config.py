import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    
    # 数据库配置
    DATABASE_NAME = os.environ.get('DATABASE_NAME') or 'eduassistant-v3'
    DATABASE_USER = os.environ.get('DATABASE_USER') or 'postgres'
    DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD') or 'rachel'
    DATABASE_HOST = os.environ.get('DATABASE_HOST') or 'localhost'
    DATABASE_PORT = int(os.environ.get('DATABASE_PORT') or 5432)
    
    # Chroma配置
    CHROMA_PERSIST_DIRECTORY = os.environ.get('CHROMA_PERSIST_DIRECTORY') or 'chroma_db'

    BOCHA_API_KEY = os.environ.get('BOCHA_API_KEY')
    BOCHA_API_URL = os.environ.get('BOCHA_API_URL') or 'https://api.bocha.cn/v1/web-search'
    BOCHA_SEARCH_COUNT = int(os.environ.get('BOCHA_SEARCH_COUNT') or 10)
    BOCHA_SEARCH_TIMEOUT = int(os.environ.get('BOCHA_SEARCH_TIMEOUT') or 10)
    BAIDU_SEARCH_API_URL = os.environ.get('BAIDU_SEARCH_API_URL') or 'https://qianfan.baidubce.com/v2/ai_search/web_search'
    BAIDU_SEARCH_API_KEY = os.environ.get('BAIDU_SEARCH_API_KEY')
    BAIDU_SEARCH_TIMEOUT = int(os.environ.get('BAIDU_SEARCH_TIMEOUT') or 10)
    BAIDU_SEARCH_TOP_K = int(os.environ.get('BAIDU_SEARCH_TOP_K') or 5)
    
    #neo4j配置
    NEO4J_URI = os.environ.get('NEO4J_URI')
    NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')
