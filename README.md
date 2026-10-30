# 运智 · 物流 Agent 前端

基于 Vue 3 + Vite 的物流业务智能助手交互页面。当前包含订单、提单与财务付款单问答、MCP 工具调用过程展示、会话列表和移动端适配。点击左侧业务模块可切换对应的独立对话。

## 启动

```bash
npm install
npm run dev
```

开发服务器会把 `/api/*` 代理到 `http://localhost:8000`。可复制 `.env.example` 为 `.env.local` 并修改 `VITE_API_TARGET`。

## Chat 接口约定

请求 `POST /chat`：

```json
{
  "message": "查询订单 OD202410180026 的状态",
  "conversation_id": "uuid"
}
```

响应示例：

```json
{
  "answer": "订单当前处于运输中。",
  "tools": [
    {
      "name": "get_order_status",
      "server": "订单 MCP Server",
      "status": "success",
      "duration_ms": 286,
      "arguments": { "order_no": "OD202410180026" },
      "result": { "status": "in_transit", "status_text": "运输中" }
    }
  ]
}
```

后端未启动时，页面会自动使用带“演示数据”标记的本地模拟结果，便于先体验完整交互。
