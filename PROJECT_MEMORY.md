# Logistics Agent 项目记忆

> 本文件用于跨会话记录项目现状。后续开始开发前，请先阅读并在完成重要改动后更新。
> 最后更新：2026-10-28（Asia/Shanghai）

## 1. 项目目标

构建物流智能助手，当前调用链如下：

```text
Vue 前端
  -> FastAPI Agent API
  -> 千问 qwen-plus（Function Calling）
  -> 订单 MCP（Streamable HTTP）
  -> MySQL wq 数据库
```

FastAPI 还会把会话消息持久化到 SQLite，作为多轮对话 Memory。

## 2. 目录结构与职责

### Vue 前端（项目根目录）

- `src/App.vue`：聊天页面，向 `POST /api/chat` 发送请求。
- `vite.config.js`：把 `/api/*` 代理到 `http://localhost:8000`，并移除 `/api` 前缀。
- 前端请求格式：

```json
{
  "message": "查询订单号 JFK24050029 的状态",
  "conversation_id": "uuid"
}
```

### `logistics_mcp/`：物流业务 MCP

- `logistics_mcp/server.py`：MCP 服务入口，注册 `get_order_detail(order_no)`。
- `logistics_mcp/tools/order.py`：订单数据库查询和状态转换。
- `logistics_mcp/database.py`：MySQL 连接配置。
- 默认 HTTP MCP 地址：`http://127.0.0.1:8001/mcp`。
- MCP 必须使用 `streamable-http` 模式，FastAPI 才能通过 HTTP 调用。

订单查询 SQL：

```sql
SELECT programme_num, examine_status
FROM tb_freight_quotation
WHERE programme_num = %s
LIMIT 1
```

数据库字段：

- 数据库：`wq`
- 表：`tb_freight_quotation`
- 订单号：`programme_num`
- 状态：`examine_status`

状态映射：

| 状态码 | 中文状态 |
| --- | --- |
| 0 | 新建 |
| 1 | 审核中 |
| 2 | 通过待流转 |
| 3 | 已确定流转 |
| 4 | 审核未通过 |
| 5 | 作废 |
| 6 | 运输中 |
| 7 | 已完结 |
| 8 | 流转异常 |
| 9 | 订单异常 |
| 10 | 已申请流转 |

### `agent_api/`：千问 Agent API 与 Memory

- `logistics_agent_api/main.py`：FastAPI 路由。
- `logistics_agent_api/llm.py`：通过 OpenAI Python SDK 的兼容接口异步调用千问。
- `logistics_agent_api/agent.py`：千问 Function Calling 与 MCP 工具编排。
- `logistics_agent_api/mcp_client.py`：订单 MCP HTTP 客户端。
- `logistics_agent_api/memory.py`：SQLite 持久化会话 Memory。
- `logistics_agent_api/config.py`：环境变量配置。
- `scripts/check_order_mcp.py`：绕过 LLM，直接检查订单 MCP。

默认模型配置：

```dotenv
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
LLM_API_STYLE=chat_completions
MCP_SERVER_URL=http://127.0.0.1:8001/mcp
```

真实密钥保存在 `agent_api/.env` 的 `DASHSCOPE_API_KEY`，不得写入源码或本文件。

## 3. FastAPI 接口

- `POST /chat`：调用千问；需要订单数据时由千问调用 `get_order_detail`，保存最终一问一答。
- `GET /conversations`：列出本地会话。
- `GET /conversations/{conversation_id}/messages`：读取会话 Memory。
- `DELETE /conversations/{conversation_id}`：删除会话和对应 Memory。
- `GET /health`：健康检查。
- Swagger：`http://127.0.0.1:8000/docs`。

`POST /chat` 响应格式与 Vue 兼容：

```json
{
  "answer": "订单号 JFK24050029 当前状态为：新建。",
  "conversation_id": "uuid",
  "tools": [
    {
      "name": "get_order_detail",
      "server": "订单 MCP Server",
      "duration_ms": 141,
      "status": "success",
      "arguments": {"order_no": "JFK24050029"},
      "result": {
        "programme_num": "JFK24050029",
        "examine_status": 0,
        "status_text": "新建"
      }
    }
  ]
}
```

## 4. 本地启动顺序

三个服务分别在三个终端运行。

### 终端一：订单 MCP

```powershell
cd D:\Dev\workspace\logistics-agent\logistics_mcp
$env:MCP_TRANSPORT = "streamable-http"
.\.venv\Scripts\python.exe -m logistics_mcp.server
```

预期监听：`127.0.0.1:8001`。

### 终端二：FastAPI Agent

```powershell
cd D:\Dev\workspace\logistics-agent\agent_api
.\.venv\Scripts\python.exe -m uvicorn logistics_agent_api.main:app --host 127.0.0.1 --port 8000
```

预期监听：`127.0.0.1:8000`。

### 终端三：Vue

```powershell
cd D:\Dev\workspace\logistics-agent
npm.cmd run dev
```

浏览器打开：`http://localhost:5173`。

说明：本机 PowerShell 禁止执行 `npm.ps1`，因此使用 `npm.cmd`。

## 5. 测试与诊断

### MCP 测试

```powershell
cd D:\Dev\workspace\logistics-agent\logistics_mcp
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Agent API 测试

```powershell
cd D:\Dev\workspace\logistics-agent\agent_api
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

最后一次运行 Agent 测试：9 项全部通过。

### 不调用千问，直接检查 MCP

```powershell
cd D:\Dev\workspace\logistics-agent\agent_api
.\.venv\Scripts\python.exe scripts\check_order_mcp.py JFK24050029
```

已确认测试订单：

```text
JFK24050029 -> examine_status=0 -> 新建
```

### 端口检查

```powershell
netstat -ano | Select-String ':5173|:8000|:8001'
```

## 6. 已解决的重要问题

### 千问没有调用 MCP

最初 FastAPI 只执行 `llm.generate()`，并硬编码返回 `tools=[]`。千问不知道订单 MCP 的存在，因而会回答“无法实时查询”。

现已在 `agent.py` 中使用千问 Function Calling：

1. 向千问声明 `get_order_detail` 工具。
2. 读取千问返回的 `tool_calls`。
3. 通过 HTTP MCP 调用真实工具。
4. 把工具结果返回千问生成最终答案。
5. 把工具轨迹同时返回 Vue。

### MCP 客户端参数错误

曾错误使用：

```python
Client(url, timeout=15)
```

MCP Python SDK 2.3 的正确参数为：

```python
Client(url, read_timeout_seconds=15)
```

该错误曾导致 `TypeError`，并被包装成“订单 MCP 服务暂时不可用”。目前已有回归测试覆盖。

### 工具失败时千问编造客服渠道

之前 MCP 失败结果仍会交给千问扩写，模型可能编造 APP、公众号和客服电话。

现已改为：当 MCP 返回失败时，FastAPI 后端直接生成受控错误，只允许提示确认订单号或稍后重试，不再让模型扩写失败信息。

### SQLite 文件被占用

SQLite 连接曾只提交事务但没有显式关闭，Windows 测试清理时出现文件占用。现在所有连接均在 `finally` 中关闭。

## 7. 安全注意事项

- 不得把 `agent_api/.env` 或 `logistics_mcp/.env` 提交到版本库。
- 不得在日志、回复或诊断命令中打印 API Key、数据库密码。
- 之前百炼 API Key 曾因旧 `.env` 异常换行意外显示在终端输出中，应在百炼控制台轮换；如果尚未轮换，这是优先事项。
- 修改 `.env` 后必须重启对应服务，运行中的进程不会自动读取新值。
- MCP 和数据库查询均应保持参数化 SQL，不拼接用户输入。

## 8. 下一步建议

- 将提单、财务、扣罚等物流工具继续添加到 `logistics_mcp/logistics_mcp/tools/`。
- 让 Agent 动态读取 MCP 工具列表，减少在 `agent.py` 中手写工具 Schema。
- 为 FastAPI 增加认证、请求日志脱敏和生产环境部署配置。
- 前端会话列表目前仍以演示数据为主，可接入 `/conversations` 和消息历史接口。
- 根据数据量评估 Memory 摘要、Token 截断和会话归档策略。

