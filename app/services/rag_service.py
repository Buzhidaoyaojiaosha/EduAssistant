import os
from typing import List, Dict
from PyPDF2 import PdfReader
from flask import current_app
from pptx import Presentation
from app.ext import knowledge_base_collection, rag_chunk_collection
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.ext import embedding_fn
from app.react.tools_register import register_as_tool
from docx import Document
from moviepy import VideoFileClip



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
        elif file_path.endswith('.docx'):
            return RAGService._extract_text_from_docx(file_path)
        elif file_path.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            return RAGService._extract_audio_from_video(file_path)
        else:
            raise ValueError("不支持的文件格式")

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
    def _extract_text_from_docx(file_path: str) -> str:
        """从 DOCX 文件中提取文本。"""
        doc = Document(file_path)
        text = ''
        for para in doc.paragraphs:
            text += para.text + '\n'
        
        print("以下是文件提取的文本内容:")
        print(text)
        return text
    
    def _extract_audio_from_video(file_path: str) -> str:
        """从视频文件中提取音频内容并转为文本。"""
        try:
            # 使用 moviepy 提取音频
            video = VideoFileClip(file_path)
            audio = video.audio
            audio_file_path = file_path.replace('.mp4', '.wav')  # 保存音频为 WAV 格式
            audio.write_audiofile(audio_file_path, fps=16000, nbytes=2, codec='pcm_s16le', ffmpeg_params=['-ac', '1'])

            # 使用音频转文本工具
            text = RAGService._convert_audio_to_text(audio_file_path)
            return text
        except Exception as e:
            raise ValueError(f"处理视频文件失败: {str(e)}")

    # @staticmethod
    # def _convert_audio_to_text(audio_file_path: str) -> str:
    #     """将音频文件转为文本（可以使用 SpeechRecognition 或其他工具）。"""
    #     import speech_recognition as sr
    #     recognizer = sr.Recognizer()

    #     try:
    #         with sr.AudioFile(audio_file_path) as source:
    #             audio_data = recognizer.record(source)
    #             text = recognizer.recognize_google(audio_data)  # 使用 Google Speech API
    #             return text
    #     except Exception as e:
    #         raise ValueError(f"音频转文本失败: {str(e)}")

    @staticmethod
    def _convert_audio_to_text(audio_file_path: str) -> str:
        """将音频文件转为文本，使用 Google Web Speech API。"""
        import speech_recognition as sr
        recognizer = sr.Recognizer()

        try:
            with sr.AudioFile(audio_file_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language="zh-CN")  # 指定中文
            return text
        except sr.UnknownValueError:
            raise ValueError("无法识别音频内容。")
        except sr.RequestError as e:
            raise ValueError(f"Google API 请求失败: {e}")
        except Exception as e:
            raise ValueError(f"音频转文本失败: {str(e)}")

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
        print(text)
        if not isinstance(text, str):
            raise ValueError(f"提取的文本不是字符串类型，文件路径: {file_path}")
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
