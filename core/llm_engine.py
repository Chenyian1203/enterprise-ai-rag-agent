# -*- coding: utf-8 -*-
import os
from openai import OpenAI
from core.rag_engine import RAGEngine

class LLMEngine:
    def __init__(self):
        # 这里用你的 DeepSeek Key
        self.client = OpenAI(
            api_key="sk-e220f79fc9e7465983c34cb893df1c07", 
            base_url="https://api.deepseek.com/v1"
        )
        self.model = "deepseek-chat"
        
        # 初始化 RAG 引擎
        doc_path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "compliance_rules.md")
        self.rag = RAGEngine(doc_path)
        
    def generate_report(self, items: list) -> str:
        print("[LLM] 开始组装 Agent 流程...")
        
        # 1. 显式化 Planning：拼装查询词去检索
        query = f"亚马逊销售商品。竞品包括: {', '.join([i['title'] for i in items])}"
        retrieved_rules = self.rag.retrieve(query, top_k=3)
        print(f"[LLM] RAG 召回片段:\n{retrieved_rules}\n")
        
        # 2. 组装 Prompt
        prompt = f"""
        你是一位资深跨境电商 COO。
        
        【由 RAG 精准召回的合规红线】
        {retrieved_rules}
        
        【真实的竞品数据】
        {items}
        
        请基于以上信息，输出一份极具落地价值的 Markdown 商业报告，包含：
        1. 竞品市场格局分析
        2. 我方差异化定价策略
        3. 必须遵守的合规红线预警
        """
        
        # 3. 调用大模型
        print("[LLM] 正在呼叫 DeepSeek...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response.choices[0].message.content