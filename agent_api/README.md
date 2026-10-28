# 物流 Agent API

FastAPI 实现的千问 Agent 后端，使用 SQLite 持久化会话 Memory，并通过
Function Calling 调用订单 MCP。接口与当前 Vue
页面的 `POST /api/chat` 请求格式兼容；Vite 会把 `/api/chat` 转发到本服务的
`POST /chat`。

## 目录职责

- `logistics_agent_api/main.py`：FastAPI 路由
- `logistics_agent_api/llm.py`：千问异步调用封装
- `logistics_agent_api/agent.py`：千问 Function Calling 与工具编排
- `logistics_agent_api/mcp_client.py`：订单 MCP HTTP 客户端
- `logistics_agent_api/memory.py`：SQLite 会话 Memory
- `logistics_agent_api/config.py`：环境变量配置

## 安装与配置

```powershell
cd D:\Dev\workspace\logistics-agent\agent_api
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

填写阿里云百炼 API Key：

```dotenv
DASHSCOPE_API_KEY=你的百炼API Key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
LLM_API_STYLE=chat_completions
MCP_SERVER_URL=http://127.0.0.1:8001/mcp
```

默认使用北京地域的公共兼容地址和 `qwen-plus`。API Key 必须属于对应地域；如果
使用其他地域或带业务空间 ID 的地址，请按百炼控制台显示的 Base URL 修改
`LLM_BASE_URL`。

## 启动

先在一个终端启动订单 MCP 的 HTTP 模式：

```powershell
cd D:\Dev\workspace\logistics-agent\logistics_mcp
$env:MCP_TRANSPORT = "streamable-http"
.\.venv\Scripts\python.exe -m logistics_mcp.server
```

再在另一个终端启动 Agent API：

```powershell
cd D:\Dev\workspace\logistics-agent\agent_api
.\.venv\Scripts\python.exe run.py
```

服务地址为 `http://127.0.0.1:8000`，接口文档为
`http://127.0.0.1:8000/docs`。保持这个服务和根目录的 Vue 开发服务同时运行，
Vue 的 `/api` 代理即可访问它。

## API

- `POST /chat`：调用千问；需要订单数据时调用 MCP，并保存一问一答
- `GET /conversations`：列出会话
- `GET /conversations/{id}/messages`：读取完整 Memory
- `DELETE /conversations/{id}`：删除会话及其 Memory
- `GET /health`：健康检查

聊天请求：

```json
{
  "message": "你好，我想查询一个订单",
  "conversation_id": "可由前端生成的 UUID"
}
```

聊天响应：

```json
{
  "answer": "你好，请提供订单号。",
  "conversation_id": "同一个 UUID",
  "tools": []
}
```

## 测试

测试使用假的 LLM，不消耗真实模型额度：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

只检查订单 MCP（不会调用千问）：

```powershell
.\.venv\Scripts\python.exe scripts/check_order_mcp.py JFK24050029
```
