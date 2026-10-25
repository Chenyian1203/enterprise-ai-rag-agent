# -*- coding: utf-8 -*-
import os
import json
import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.rag_engine import RAGEngine
from openai import OpenAI

app = FastAPI(title="企业级 AI 多 Agent 运营中台")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 初始化 RAG 和 大模型
doc_path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "compliance_rules.md")
rag = RAGEngine(doc_path)
client = OpenAI(api_key="sk-e220f79fc9e7465983c34cb893df1c07", base_url="https://api.deepseek.com/v1")

class ChatRequest(BaseModel):
    user_input: str
    history: list = [] # 用于多轮对话记忆

# 🚨 核心升级：带意图路由的流式对话接口
@app.post("/api/chat")
async def chat_stream(request: ChatRequest):
    user_input = request.user_input
    
    # 🧠 第一步：意图识别（让大模型先判断该调用哪个 Agent）
    router_prompt = f"""
    你是一个电商 AI 运营中台的意图路由器。
    请判断用户的输入属于以下哪个场景（只输出场景名称）：
    1. 选品分析 (用户想了解选品、竞品价格、市场机会)
    2. 合规审查 (用户想排查违禁词、Listing 风险)
    3. 客服回复 (用户想回复买家消息)

    用户的输入是: {user_input}
    """
    router_res = client.chat.completions.create(
        model="deepseek-chat", 
        messages=[{"role": "user", "content": router_prompt}],
        temperature=0.1
    )
    intent = router_res.choices[0].message.content.strip()
    
    # 🧠 第二步：根据意图分发
    def generate():
        yield f"data: {json.dumps({'text': f'🤖 [路由中心] 识别到意图: {intent}，正在调起对应 Agent...\n\n'})}\n\n"
        
        # 如果是合规审查，去 RAG 知识库检索
        context = ""
        if "合规" in intent:
            context = f"\n【RAG知识库召回】\n{rag.retrieve(user_input, top_k=2)}"
            
        # 组装给最终 Agent 的 Prompt
        agent_prompt = f"""
        你是一个资深的电商业务专家（当前场景: {intent}）。
        请根据以下信息回答用户问题。
        {context}
        用户输入: {user_input}
        """
        
        # 流式调用大模型
        response = client.chat.completions.create(
            model="deepseek-chat", 
            messages=[{"role": "user", "content": agent_prompt}], 
            stream=True
        )
        
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield f"data: {json.dumps({'text': chunk.choices[0].delta.content})}\n\n"
        yield "data: [DONE]\n\n"
        
    return StreamingResponse(generate(), media_type="text/event-stream")

# 保留之前的真实数据接口，供前端图表渲染
@app.get("/api/get_real_products")
def get_real_products():
    response = requests.get("https://dummyjson.com/products?limit=5")
    data = response.json()
    products = [{"title": item["title"], "brand": item["brand"], "price": item["price"], "rating": item["rating"], "img": item["thumbnail"]} for item in data["products"]]
    return {"status": "success", "products": products}

@app.get("/")
def home():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))