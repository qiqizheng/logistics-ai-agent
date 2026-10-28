"""物流 MCP 服务入口。"""

from __future__ import annotations

import logging
import os
from typing import Literal, cast

import pymysql
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from logistics_mcp.tools.order import (
    OrderDetail,
    OrderNotFoundError,
    query_order_detail,
)


logger = logging.getLogger(__name__)
mcp = MCPServer(
    "物流业务 MCP Server",
    instructions="提供订单、提单、财务和扣罚等物流业务信息查询。",
)


@mcp.tool()
def get_order_detail(order_no: str) -> OrderDetail:
    """输入订单号，查询订单当前状态。订单号对应 programme_num 字段。"""
    try:
        return query_order_detail(order_no)
    except (ValueError, OrderNotFoundError) as exc:
        raise ToolError(str(exc)) from exc
    except pymysql.MySQLError as exc:
        logger.exception("查询订单状态时数据库访问失败")
        raise ToolError("订单查询暂时失败，请检查数据库连接或稍后重试") from exc


def run() -> None:
    """按照环境变量选择 MCP 传输方式并启动服务。"""
    transport_name = os.getenv("MCP_TRANSPORT", "stdio")
    allowed_transports = {"stdio", "streamable-http"}
    if transport_name not in allowed_transports:
        raise ValueError(
            f"不支持 MCP_TRANSPORT={transport_name!r}，可选值为 stdio、streamable-http"
        )

    transport = cast(Literal["stdio", "streamable-http"], transport_name)
    if transport == "streamable-http":
        mcp.run(
            transport=transport,
            host=os.getenv("MCP_HOST", "127.0.0.1"),
            port=int(os.getenv("MCP_PORT", "8001")),
            json_response=True,
        )
        return

    mcp.run(transport=transport)


if __name__ == "__main__":
    run()

