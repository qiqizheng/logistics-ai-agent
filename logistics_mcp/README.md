# 物流业务 MCP Server

Python 实现的物流业务 MCP 服务。当前提供订单状态查询，后续可以在
`logistics_mcp/tools/` 下继续增加提单、财务、扣罚等工具模块。

## 当前工具

### `get_order_detail(order_no)`

使用订单号查询 `wq.tb_freight_quotation`：

```sql
SELECT programme_num, examine_status
FROM tb_freight_quotation
WHERE programme_num = %s
LIMIT 1
```

返回示例：

```json
{
  "programme_num": "OD202410180026",
  "examine_status": 6,
  "status_text": "运输中"
}
```

## 安装

要求 Python 3.10 或更高版本。在本目录执行：

```powershell
cd D:\Dev\workspace\logistics-agent\logistics_mcp
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

打开 `.env`，填写本地 MySQL 的 `DB_USER` 和 `DB_PASSWORD`。默认数据库名已经是
`wq`，不要提交包含真实密码的 `.env`。

## 启动

本地 MCP 客户端通常使用 stdio：

```powershell
.\.venv\Scripts\python.exe -m logistics_mcp.server
```

如需通过 HTTP 连接：

```powershell
$env:MCP_TRANSPORT = "streamable-http"
.\.venv\Scripts\python.exe -m logistics_mcp.server
```

MCP 地址为 `http://127.0.0.1:8001/mcp`。HTTP 模式只监听本机地址。

也可以用 MCP Inspector 调试：

```powershell
.\.venv\Scripts\mcp.exe dev logistics_mcp/server.py
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

