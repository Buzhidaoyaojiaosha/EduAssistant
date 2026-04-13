# extensions
from openai import OpenAI
from playhouse.postgres_ext import PostgresqlExtDatabase
from chromadb import PersistentClient
import os
from neo4j import GraphDatabase

db = PostgresqlExtDatabase(None)

chroma_client = None
knowledge_base_collection = None
rag_chunk_collection = None
graph = None
embedding_fn = None


def initialize_extensions():
    # initialize database
    db.init(os.getenv("DATABASE_NAME"),
            host=os.getenv("DATABASE_HOST"),
            user=os.getenv("DATABASE_USER"),
            password=os.getenv("DATABASE_PASSWORD"),
            port=os.getenv("DATABASE_PORT"))

    class OpenAIEmbeddingsV1:
        def __init__(self, api_key, model="text-embedding-3-small"):
            self.client = OpenAI(api_key=api_key,base_url=os.getenv("OPENAI_API_BASE"))
            self.model = model

        def __call__(self, texts):
            response = self.client.embeddings.create(input=texts, model=self.model)
            return [item.embedding for item in response.data]

    global embedding_fn
    embedding_fn = OpenAIEmbeddingsV1(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="text-embedding-3-small"
    )

    # initialize chroma
    global chroma_client
    chroma_client = PersistentClient(path=os.getenv("CHROMA_PERSIST_DIRECTORY"))

    global knowledge_base_collection, rag_chunk_collection

    knowledge_base_collection = chroma_client.get_or_create_collection("knowledge_base")
    # 用于rag功能的collection
    rag_chunk_collection = chroma_client.get_or_create_collection("rag_chunk",
                                                                  embedding_function=embedding_fn)

    # initialize graph
    global graph
    with GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))) as graph:
            graph.verify_connectivity()
            print("Connected to Neo4j successfully!")

