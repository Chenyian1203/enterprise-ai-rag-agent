# -*- coding: utf-8 -*-
import os
import chromadb
from sentence_transformers import SentenceTransformer

class RAGEngine:
    def __init__(self, doc_path: str):
        print("[RAG] 初始化向量数据库与本地 Embedding 模型...")
        # 1. 加载本地免费的中文 Embedding 模型
        self.model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
        
        # 2. 初始化本地 ChromaDB 客户端（数据持久化到 core/chroma_db）
        db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
        self.client = chromadb.PersistentClient(path=db_path)
        
        # 3. 创建/获取集合
        self.collection = self.client.get_or_create_collection(name="compliance_rules")
        
        # 4. 如果是第一次运行，自动执行文档切片与向量化入库
        if self.collection.count() == 0:
            self._ingest_document(doc_path)
            
    def _ingest_document(self, doc_path: str):
        print(f"[RAG] 读取并切片文档: {doc_path}")
        if not os.path.exists(doc_path):
            print("[RAG] ⚠️ 找不到合规文档，跳过。")
            return
            
        with open(doc_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        # 切片策略：按行切分，过滤掉无意义的短行
        chunks = [chunk.strip() for chunk in text.split('\n') if len(chunk.strip()) > 10]
        
        if not chunks:
            return
            
        print(f"[RAG] 共切分 {len(chunks)} 个文本块，正在向量化...")
        # 文本转向量
        embeddings = self.model.encode(chunks).tolist()
        
        # 存入向量数据库
        self.collection.add(
            embeddings=embeddings,
            documents=chunks,
            ids=[f"chunk_{i}" for i in range(len(chunks))]
        )
        print("[RAG] ✅ 知识库入库完成！")

    def retrieve(self, query: str, top_k: int = 3) -> str:
        """根据查询词，语义检索最相关的合规片段"""
        if self.collection.count() == 0:
            return "暂无合规规则。"
            
        print(f"[RAG] 正在语义检索: '{query}' ...")
        query_embedding = self.model.encode([query]).tolist()
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )
        
        if results and results['documents'] and len(results['documents']) > 0:
            return "\n".join(results['documents'][0])
        return "暂无相关合规规则。"