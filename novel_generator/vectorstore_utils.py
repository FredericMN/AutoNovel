#novel_generator/vectorstore_utils.py
# -*- coding: utf-8 -*-
"""
向量库相关操作（初始化、更新、检索、清空、文本切分等）
"""
import os
import logging
import traceback
import nltk
import numpy as np
import re
import ssl
import requests
import warnings
import hashlib
from langchain_chroma import Chroma
logging.basicConfig(
    filename='app.log',      # 日志文件名
    filemode='a',            # 追加模式（'w' 会覆盖）
    level=logging.INFO,      # 记录 INFO 及以上级别的日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# 禁用特定的Torch警告
warnings.filterwarnings('ignore', message='.*Torch was not compiled with flash attention.*')
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # 禁用tokenizer并行警告

from chromadb.config import Settings
from langchain.docstore.document import Document
from sklearn.metrics.pairwise import cosine_similarity
from .common import call_with_retry

def get_vectorstore_dir(filepath: str) -> str:
    """获取 vectorstore 路径"""
    return os.path.join(filepath, "vectorstore")

def clear_vector_store(filepath: str) -> bool:
    """清空 清空向量库"""
    import shutil
    store_dir = get_vectorstore_dir(filepath)
    if not os.path.exists(store_dir):
        logging.info("No vector store found to clear.")
        return False
    try:
        shutil.rmtree(store_dir)
        logging.info(f"Vector store directory '{store_dir}' removed.")
        return True
    except Exception as e:
        logging.error(f"无法删除向量库文件夹，请关闭程序后手动删除 {store_dir}。\n {str(e)}")
        traceback.print_exc()
        return False

def init_vector_store(embedding_adapter, texts, filepath: str):
    """
    在 filepath 下创建/加载一个 Chroma 向量库并插入 texts。
    如果Embedding失败，则返回 None，不中断任务。
    """
    from langchain.embeddings.base import Embeddings as LCEmbeddings

    store_dir = get_vectorstore_dir(filepath)
    os.makedirs(store_dir, exist_ok=True)
    documents = [Document(page_content=str(t)) for t in texts]

    try:
        class LCEmbeddingWrapper(LCEmbeddings):
            def embed_documents(self, texts):
                return call_with_retry(
                    func=embedding_adapter.embed_documents,
                    max_retries=3,
                    fallback_return=[],
                    texts=texts
                )
            def embed_query(self, query: str):
                res = call_with_retry(
                    func=embedding_adapter.embed_query,
                    max_retries=3,
                    fallback_return=[],
                    query=query
                )
                return res

        chroma_embedding = LCEmbeddingWrapper()
        vectorstore = Chroma.from_documents(
            documents,
            embedding=chroma_embedding,
            persist_directory=store_dir,
            client_settings=Settings(anonymized_telemetry=False),
            collection_name="novel_collection"
        )
        return vectorstore
    except Exception as e:
        logging.warning(f"Init vector store failed: {e}")
        traceback.print_exc()
        return None

def load_vector_store(embedding_adapter, filepath: str):
    """
    读取已存在的 Chroma 向量库。若不存在则返回 None。
    如果加载失败（embedding 或IO问题），则返回 None。
    """
    from langchain.embeddings.base import Embeddings as LCEmbeddings
    store_dir = get_vectorstore_dir(filepath)
    if not os.path.exists(store_dir):
        logging.info("Vector store not found. Will return None.")
        return None

    try:
        class LCEmbeddingWrapper(LCEmbeddings):
            def embed_documents(self, texts):
                return call_with_retry(
                    func=embedding_adapter.embed_documents,
                    max_retries=3,
                    fallback_return=[],
                    texts=texts
                )
            def embed_query(self, query: str):
                res = call_with_retry(
                    func=embedding_adapter.embed_query,
                    max_retries=3,
                    fallback_return=[],
                    query=query
                )
                return res

        chroma_embedding = LCEmbeddingWrapper()
        return Chroma(
            persist_directory=store_dir,
            embedding_function=chroma_embedding,
            client_settings=Settings(anonymized_telemetry=False),
            collection_name="novel_collection"
        )
    except Exception as e:
        logging.warning(f"Failed to load vector store: {e}")
        traceback.print_exc()
        return None

def split_by_length(text: str, max_length: int = 500):
    """按照 max_length 切分文本"""
    segments = []
    start_idx = 0
    while start_idx < len(text):
        end_idx = min(start_idx + max_length, len(text))
        segment = text[start_idx:end_idx]
        segments.append(segment.strip())
        start_idx = end_idx
    return segments



def split_text_for_vectorstore(chapter_text: str, max_length: int = 500, similarity_threshold: float = 0.7):
    """
    对新的章节文本进行分段后,再用于存入向量库。
    强依赖 NLTK 分句：程序启动与此处都会确保 punkt / punkt_tab 存在；若缺失则尝试下载。
    下载失败将抛出异常以便用户修复网络/代理。
    """
    if not chapter_text.strip():
        return []

    # Ensure NLTK resources are available (punkt / punkt_tab)
    from nltk_setup import ensure_nltk_punkt_resources
    ensure_nltk_punkt_resources()

    import nltk
    sentences = nltk.sent_tokenize(chapter_text)
    if not sentences:
        return []

    # 直接按长度分段,不做相似度合并
    final_segments = []
    current_segment = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence)
        if current_length + sentence_length > max_length:
            if current_segment:
                final_segments.append(" ".join(current_segment))
            current_segment = [sentence]
            current_length = sentence_length
        else:
            current_segment.append(sentence)
            current_length += sentence_length

    if current_segment:
        final_segments.append(" ".join(current_segment))

    return final_segments
def update_vector_store(embedding_adapter, new_chapter: str, filepath: str):
    """
    将最新章节文本插入到向量库中。
    若库不存在则初始化；若初始化/更新失败，则跳过。
    """
    from utils import read_file, clear_file_content, save_string_to_txt
    splitted_texts = split_text_for_vectorstore(new_chapter)
    if not splitted_texts:
        logging.warning("No valid text to insert into vector store. Skipping.")
        return

    store = load_vector_store(embedding_adapter, filepath)
    if not store:
        logging.info("Vector store does not exist or failed to load. Initializing a new one for new chapter...")
        store = init_vector_store(embedding_adapter, splitted_texts, filepath)
        if not store:
            logging.warning("Init vector store failed, skip embedding.")
        else:
            logging.info("New vector store created successfully.")
        return

    try:
        docs = [Document(page_content=str(t)) for t in splitted_texts]
        store.add_documents(docs)
        logging.info("Vector store updated with the new chapter splitted segments.")
    except Exception as e:
        logging.warning(f"Failed to update vector store: {e}")
        traceback.print_exc()

def get_relevant_context_from_vector_store(embedding_adapter, query: str, filepath: str, k: int = 2) -> str:
    """
    从向量库中检索与 query 最相关的 k 条文本，拼接后返回。
    如果向量库加载/检索失败，则返回空字符串。
    最终只返回最多2000字符的检索片段。
    """
    store = load_vector_store(embedding_adapter, filepath)
    if not store:
        logging.info("No vector store found or load failed. Returning empty context.")
        return ""

    try:
        docs = store.similarity_search(query, k=k)
        if not docs:
            logging.info(f"No relevant documents found for query '{query}'. Returning empty context.")
            return ""
        combined = "\n".join([d.page_content for d in docs])
        if len(combined) > 2000:
            combined = combined[:2000]
        return combined
    except Exception as e:
        logging.warning(f"Similarity search failed: {e}")
        traceback.print_exc()
        return ""

def get_relevant_contexts_deduplicated(
    embedding_adapter,
    query_groups: list,
    filepath: str,
    k_per_group: int = 2,
    max_total_results: int = None
) -> list:
    """
    对多组关键词执行向量检索并去重,返回去重后的文档内容列表。

    Args:
        embedding_adapter: Embedding适配器
        query_groups: 关键词组列表,如 ["科技公司 数据泄露", "地下实验室 基因编辑"]
        filepath: 项目文件路径
        k_per_group: 每组关键词检索的文档数量
        max_total_results: 最大返回结果数(None表示不限制)

    Returns:
        list: 去重后的文档内容列表,每个元素为 {"content": str, "queries": [str], "type": str}
              其中 queries 包含所有命中该文档的关键词组
    """
    store = load_vector_store(embedding_adapter, filepath)
    if not store:
        logging.info("No vector store found or load failed. Returning empty list.")
        return []

    try:
        collection_size = store._collection.count()
        if collection_size == 0:
            logging.info("Vector store is empty. Returning empty list.")
            return []

        # 动态调整每组检索数量
        # 如果关键词组很多,减少每组数量避免过度检索
        num_groups = len(query_groups)
        if num_groups > 5:
            adjusted_k = max(1, k_per_group // 2)
        elif num_groups > 3:
            adjusted_k = k_per_group
        else:
            adjusted_k = min(k_per_group * 2, collection_size)

        logging.info(f"Retrieving {adjusted_k} docs per group from {num_groups} keyword groups (collection size: {collection_size})")

        # 收集所有候选文档，使用字典来跟踪相同文档的多个query
        docs_by_hash = {}  # hash -> {"content": str, "queries": [str], "type": str}
        seen_hashes = set()

        for query in query_groups:
            # 检索文档
            docs = store.similarity_search(query, k=adjusted_k)

            for doc in docs:
                content = doc.page_content

                # 使用稳定的SHA1哈希进行去重（与monitor模块保持一致）
                content_hash = hashlib.sha1(
                    (content[:400] if len(content) > 400 else content).encode('utf-8', errors='ignore')
                ).hexdigest()

                # 判断内容类型
                doc_type = "GENERAL"
                if any(kw in query.lower() for kw in ["技法", "手法", "模板", "写作"]):
                    doc_type = "TECHNIQUE"
                elif any(kw in query.lower() for kw in ["设定", "技术", "世界观"]):
                    doc_type = "SETTING"

                if content_hash not in seen_hashes:
                    # 首次见到该文档
                    seen_hashes.add(content_hash)
                    docs_by_hash[content_hash] = {
                        "content": content,
                        "queries": [query],
                        "type": doc_type
                    }
                else:
                    # 文档已存在，添加新的query到列表
                    docs_by_hash[content_hash]["queries"].append(query)
                    # 类型优先级：TECHNIQUE > SETTING > GENERAL
                    if doc_type == "TECHNIQUE" or (doc_type == "SETTING" and docs_by_hash[content_hash]["type"] == "GENERAL"):
                        docs_by_hash[content_hash]["type"] = doc_type

                # 达到总量上限则提前结束
                if max_total_results and len(docs_by_hash) >= max_total_results:
                    logging.info(f"Reached max total results limit: {max_total_results}")
                    break

            if max_total_results and len(docs_by_hash) >= max_total_results:
                break

        # 转换为列表返回
        all_docs_with_info = list(docs_by_hash.values())
        logging.info(f"Retrieved {len(all_docs_with_info)} unique documents (total queries across docs: {sum(len(d['queries']) for d in all_docs_with_info)})")
        return all_docs_with_info

    except Exception as e:
        logging.error(f"Batch similarity search failed: {e}")
        traceback.print_exc()
        return []

def _get_sentence_transformer(model_name: str = 'paraphrase-MiniLM-L6-v2'):
    """获取sentence transformer模型，处理SSL问题"""
    try:
        # 设置torch环境变量
        os.environ["TORCH_ALLOW_TF32_CUBLAS_OVERRIDE"] = "0"
        os.environ["TORCH_CUDNN_V8_API_ENABLED"] = "0"
        
        # 禁用SSL验证
        ssl._create_default_https_context = ssl._create_unverified_context
        
        # ...existing code...
    except Exception as e:
        logging.error(f"Failed to load sentence transformer model: {e}")
        traceback.print_exc()
        return None



