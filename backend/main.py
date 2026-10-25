# -*- coding: utf-8 -*-
import os
import json
import requests # 🚨 引入 requests 去请求真实数据
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.rag_engine import RAGEngine
from openai import OpenAI

app = FastAPI(title="企业级 AI RAG Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

doc_path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "compliance_rules.md")
rag = RAGEngine(doc_path)
client = OpenAI(api_key="sk-e220f79fc9e7465983c34cb893df1c07", base_url="https://api.deepseek.com/v1")

# 🚨 新增接口：去真实的公网抓取真实数据！
@app.get("/api/get_real_products")
def get_real_products():
    print("[Data] 正在去 DummyJSON 抓取真实的全球商品数据...")
    # 去真实的公网拉取 5 个真实的商品
    response = requests.get("https://dummyjson.com/products?limit=5")
    data = response.json()
    
    products = []
    for item in data["products"]:
        products.append({
            "title": item["title"],
            "brand": item["brand"],
            "price": item["price"],
            "rating": item["rating"],
            "img": item["thumbnail"] # 真实的商品图片链接
        })
    print(f"[Data] ✅ 成功抓取 {len(products)} 条真实商品！")
    return {"status": "success", "products": products}

class TaskRequest(BaseModel):
    competitors: list

@app.post("/api/analyze_stream")
async def analyze_stream(request: TaskRequest):
    query = f"竞品包括: {', '.join([i['title'] for i in request.competitors])}"
    retrieved_rules = rag.retrieve(query, top_k=3)
    
    prompt = f"""
    你是一位资深跨境电商 COO。
    【合规红线】{retrieved_rules}
    【竞品数据】{request.competitors}
    请生成包含市场格局、定价策略、合规红线的 Markdown 商业报告。
    """
    
    def generate():
        response = client.chat.completions.create(
            model="deepseek-chat", messages=[{"role": "user", "content": prompt}], stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield f"data: {json.dumps({'text': chunk.choices[0].delta.content})}\n\n"
        yield "data: [DONE]\n\n"
        
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/")
def home():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))