# 🚀 企业级跨境电商 AI 多 Agent 运营中台

本项目是一个面向 B 端业务人员的全栈 AI 商业应用。通过 FastAPI 后端、ChromaDB 向量检索、LangGraph 状态机编排与 DeepSeek 大模型，实现了**意图路由、合规溯源、流式大屏及 Token 成本监控**的全链路闭环。

👉 **[点击查看效果展示视频](./效果展示.mp4)**

## 🏗️ 核心架构
- **智能路由层**：基于 LangGraph 构建 StateGraph，实现意图识别与动态任务分发。
- **AI 引擎**：ChromaDB (向量检索 RAG) + DeepSeek API (流式生成)。
- **前端**：ECharts 数据可视化 + SSE 流式打字机交互。
- **工程化**：`.env` 密钥隔离、`Dockerfile` 容器化部署、企业级日志追踪。

## 🌟 核心亮点
1. **真正的 Multi-Agent 编排**：不仅调用 API，更实现“识别意图 -> 分发节点 -> 最终生成”的图编排架构。
2. **高可用降级容灾**：公网数据抓取失败自动回退至高保真快照，保证大屏 7x24 小时不白屏。
3. **成本监控**：实时计算并展示每次请求的 Token 消耗，具备商业成本意识。

## 🚀 一键启动 (Docker)
```bash
docker build -t ai-agent .
docker run -p 8000:8000 ai-agent
## 🚀 本地运行 
pip install -r requirements.txt
cd backend
uvicorn main:app --reload
# 访问 http://127.0.0.1:8000/

3. 页面往下滑，点击绿色的 **`Commit changes`** 按钮。

---
