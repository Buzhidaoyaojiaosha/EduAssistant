import os
from typing import List, Dict
from PyPDF2 import PdfReader
from flask import current_app
from pptx import Presentation
from app.ext import knowledge_base_collection, rag_chunk_collection
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.ext import embedding_fn
from app.react.tools_register import register_as_tool


class RAGService:
    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
        """从文件中提取文本内容。支持 PDF 和 PPTX 格式。"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件未找到: {file_path}")

        if file_path.endswith('.pdf'):
            return RAGService._extract_text_from_pdf(file_path)
        elif file_path.endswith('.pptx'):
            return RAGService._extract_text_from_pptx(file_path)
        else:
            raise ValueError("不支持的文件格式，仅支持 PDF 和 PPTX")

    @staticmethod
    def _extract_text_from_pdf(file_path: str) -> str:
        """从 PDF 文件中提取文本。"""
        text = ''
        with open(file_path, 'rb') as file:
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + '\n'
        return text

    @staticmethod
    def _extract_text_from_pptx(file_path: str) -> str:
        """从 PPTX 文件中提取文本。"""
        text = ''
        prs = Presentation(file_path)
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, 'text'):
                    text += shape.text + '\n'
        return text

    @staticmethod
    def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
        """将文本切分为多个片段。"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ".", "。", "！", "？", "，", " "]
        )
        return text_splitter.split_text(text)

    @staticmethod
    def process_and_store_file(file_path: str, file_url: str, title: str, course_id: int = None,

                               category: str = None, tags: List[str] = None) :
        """
        处理文件，提取文本，切分内容，并存储到向量数据库和关系数据库。

        Args:
            file_path: 文件本地路径
            file_url: 文件oss路径
            title: 知识条目标题
            course_id: 关联的课程 ID
            category: 分类
            tags: 标签列表

        Returns:
            包含原始记录和切分片段信息的字典
        """
        # 提取文本并切分
        text = RAGService.extract_text_from_file(file_path)
        chunks = RAGService.split_text(text)

        # 保存切分片段到 rag_chunk_collection
        ids = []
        documents = []
        metadatas = []
        for index, chunk in enumerate(chunks):
            doc_id = f"{title}_片段{index}"
            ids.append(doc_id)
            documents.append(chunk)
            metadata = {
                "title": f"{title}_片段{index}",
                "type": "1",
                "course_id": course_id,
                "category": category,
                "tags": ",".join(tags) if tags else "",
                "is_chunk": True,
                "chunk_index": index,
                "source_file": file_url
            }
            metadatas.append(metadata)

            # 将切分片段添加到向量数据库
            rag_chunk_collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embedding_fn(documents)
            )

        # # 保存切分片段
        # for index, chunk in enumerate(chunks):
        #     KnowledgeBaseService.add_knowledge(
        #         title=f"{title}_片段{index}",
        #         type=1,
        #         content=chunk,
        #         course_id=course_id,
        #         category=category,
        #         tags=tags,
        #         is_chunk=True,
        #         chunk_index=index,
        #         source_file=file_url
        #     )

    @staticmethod
    def delete_chunks_by_source_url(self, source_url):
        """
        根据 source_url 删除向量数据库中 is_chunk 为 true 的记录
        :param source_url: 文件的源 URL
        """
        try:
            # 查询满足条件的记录的 ID
            results = knowledge_base_collection.get(
                where={"$and": [{"is_chunk": True}, {"source_file": source_url}]}
            )
            ids = results.get("ids", [])

            if ids:
                # 删除匹配的记录
                knowledge_base_collection.delete(ids=ids)
                rag_chunk_collection.delete(ids=ids)
                return True
            return False
        except Exception as e:
            current_app.logger.error(f"删除向量数据库记录失败: {str(e)}")
            return False


    @register_as_tool(roles=["student", "teacher"])
    @staticmethod
    def search_docs(query, top_k=3):
        """基于给定查询在向量数据库中搜索相关文档片段。
        Args:
            query: 用于搜索的查询文本。
            top_k: 返回的相关文档片段的最大数量，默认为3。

        Returns:
            str: 包含匹配文档片段及其来源信息的字符串，各片段间用换行符分隔。

        Raises:
            Exception: 当向量数据库查询过程中出现错误时抛出。
        """

        embedding = embedding_fn([query])  # embedding_fn 是 OpenAI 或 sentence-transformers

        results = rag_chunk_collection.query(
            query_embeddings=embedding,
            n_results=top_k,
            where={"is_chunk": True}  # 只搜索切片数据
        )

        # 提取文本片段和来源
        docs = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            docs.append(f"《{meta['title']}》第{meta['chunk_index']}段：{doc}")

        return "\n".join(docs)
