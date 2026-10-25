# -*- coding: utf-8 -*-
import os
import json
import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sys
from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.rag_engine import RAGEngine
from openai import OpenAI

app = FastAPI(title="企业级 AI 多 Agent 运营中台")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

doc_path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "compliance_rules.md")
rag = RAGEngine(doc_path)
client = OpenAI(api_key="sk-e220f79fc9e7465983c34cb893df1c07", base_url="https://api.deepseek.com/v1")

# 企业级监控：Token 记录
TOKEN_USAGE = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

class ChatRequest(BaseModel):
    user_input: str

class AgentState(TypedDict):
    user_input: str
    intent: str
    context: str
    response: str

# ================= LangGraph 节点 =================
def router_node(state: AgentState):
    prompt = f"判断用户输入意图，只输出以下三个词之一（选品分析、合规审查、客服回复）：{state['user_input']}"
    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}], temperature=0.1)
    if res.usage:
        TOKEN_USAGE["prompt_tokens"] += res.usage.prompt_tokens
        TOKEN_USAGE["completion_tokens"] += res.usage.completion_tokens
        TOKEN_USAGE["total_tokens"] += res.usage.total_tokens
    return {"intent": res.choices[0].message.content.strip()}

def compliance_node(state: AgentState):
    context = rag.retrieve(state['user_input'], top_k=2)
    return {"context": f"【合规规则库】\n{context}"}

def selection_node(state: AgentState):
    return {"context": "【选品策略库】\n当前市场红海价格为$20-$35，建议主推差异化功能。"}

def customer_service_node(state: AgentState):
    return {"context": "【客服安抚政策】\n对于物流延误，建议赔偿5美金优惠券并真诚道歉。"}

def generate_node(state: AgentState):
    prompt = f"你是资深电商专家。当前意图：{state['intent']}。背景信息：{state['context']}。用户需求：{state['user_input']}。请给出专业回答。"
    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}])
    if res.usage:
        TOKEN_USAGE["prompt_tokens"] += res.usage.prompt_tokens
        TOKEN_USAGE["completion_tokens"] += res.usage.completion_tokens
        TOKEN_USAGE["total_tokens"] += res.usage.total_tokens
    return {"response": res.choices[0].message.content}

# ================= 编译 LangGraph =================
workflow = StateGraph(AgentState)
workflow.add_node("router", router_node)
workflow.add_node("compliance", compliance_node)
workflow.add_node("selection", selection_node)
workflow.add_node("customer_service", customer_service_node)
workflow.add_node("generate", generate_node)

workflow.set_entry_point("router")

def route_intent(state: AgentState) -> Literal["compliance", "selection", "customer_service"]:
    intent = state.get("intent", "")
    if "合规" in intent: return "compliance"
    if "选品" in intent: return "selection"
    return "customer_service"

workflow.add_conditional_edges("router", route_intent)
workflow.add_edge("compliance", "generate")
workflow.add_edge("selection", "generate")
workflow.add_edge("customer_service", "generate")
workflow.add_edge("generate", END)

agent_app = workflow.compile()

# ================= 核心 API 接口 =================
@app.post("/api/chat")
async def chat_stream(request: ChatRequest):
    def generate():
        yield f"data: {json.dumps({'text': '🔄 [LangGraph 引擎] 开始动态编排...\n\n'})}\n\n"
        initial_state = {"user_input": request.user_input}
        final_state = agent_app.invoke(initial_state)
        
        yield f"data: {json.dumps({'text': f'🧠 [意图路由] 识别为：**{final_state['intent']}**，流转至对应 Agent\n\n'})}\n\n"
        for char in final_state["response"]:
            yield f"data: {json.dumps({'text': char})}\n\n"
            import time; time.sleep(0.01)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/api/token_usage")
def get_token_usage():
    return TOKEN_USAGE

# 🚨 企业级容灾数据源
@app.get("/api/get_real_products")
def get_real_products():
    try:
        # 尝试请求真实公网（极大概率会因为网络波动失败，所以必须写 try-except）
        response = requests.get("https://dummyjson.com/products?limit=5", timeout=3)
        data = response.json()
        products = [{"title": item["title"], "brand": item["brand"], "price": item["price"], "rating": item["rating"], "img": item["thumbnail"]} for item in data["products"]]
        return {"status": "success", "source": "Real-Time API", "products": products}
    except Exception as e:
        # 🚨 失败时，无缝降级到高保真快照数据，绝不让前端白屏！
        print(f"[Data] 公网接口请求超时，启动高可用降级方案：{e}")
        fallback_products = [
            {"title": "Ninja Blast Portable Blender", "brand": "Ninja", "price": 49.99, "rating": 4.6, "img": "https://m.media-amazon.com/images/I/61K-j-x-m-L._AC_UL320_.jpg"},
            {"title": "SWEETFULL Portable Blender", "brand": "SWEETFULL", "price": 29.99, "rating": 4.5, "img": "https://m.media-amazon.com/images/I/71V1v1p4K-L._AC_UL320_.jpg"},
            {"title": "BlendJet 2 16oz", "brand": "BlendJet", "price": 49.95, "rating": 4.4, "img": "https://m.media-amazon.com/images/I/61N9gW8bS0L._AC_UL320_.jpg"},
            {"title": "Hamilton Beach Personal", "brand": "Hamilton Beach", "price": 34.99, "rating": 4.3, "img": "https://m.media-amazon.com/images/I/71s7vHkLw-L._AC_UL320_.jpg"},
            {"title": "COKUNST with LED", "brand": "COKUNST", "price": 27.99, "rating": 4.2, "img": "https://m.media-amazon.com/images/I/71B-H+e7TXL._AC_UL320_.jpg"}
        ]
        return {"status": "success", "source": "High-Availability Fallback", "products": fallback_products}

@app.get("/")
def home():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))