# extensions

from playhouse.postgres_ext import PostgresqlExtDatabase
from chromadb import PersistentClient
import os
# from py2neo import Graph  # 注释掉py2neo

db = PostgresqlExtDatabase(None)

chroma_client = None
knowledge_base_collection = None
# graph = None  # 注释掉graph

def initialize_extensions():
    # initialize database
    db.init(os.getenv("DATABASE_NAME"),
            host=os.getenv("DATABASE_HOST"),
            user=os.getenv("DATABASE_USER"),
            password=os.getenv("DATABASE_PASSWORD"),
            port=os.getenv("DATABASE_PORT"))
    
    # initialize chroma
    global chroma_client
    chroma_client = PersistentClient(path=os.getenv("CHROMA_PERSIST_DIRECTORY"))
    global knowledge_base_collection
    knowledge_base_collection = chroma_client.get_or_create_collection("knowledge_base")
    
    # global graph
    # graph =Graph(
    #     os.getenv("NEO4J_URI"),
    #     auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
    # )


