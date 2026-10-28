"""订单 MCP 的 HTTP 客户端。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mcp import Client


@dataclass(frozen=True)
class MCPToolResult:
    status: str
    result: dict[str, Any] | str


class OrderMCPClient:
    def __init__(self, server_url: str, timeout_seconds: float = 15) -> None:
        self.server_url = server_url
        self.timeout_seconds = timeout_seconds

    async def get_order_detail(self, order_no: str) -> MCPToolResult:
        """通过 Streamable HTTP 调用订单 MCP。"""
        async with Client(
            self.server_url,
            read_timeout_seconds=self.timeout_seconds,
        ) as client:
            response = await client.call_tool(
                "get_order_detail", {"order_no": order_no}
            )

        if response.is_error:
            message = "；".join(
                block.text
                for block in response.content
                if hasattr(block, "text") and block.text
            )
            return MCPToolResult(
                status="error",
                result=message or "订单查询失败",
            )

        structured = response.structured_content
        if isinstance(structured, dict):
            return MCPToolResult(status="success", result=structured)

        text = "\n".join(
            block.text
            for block in response.content
            if hasattr(block, "text") and block.text
        )
        return MCPToolResult(status="success", result=text)
