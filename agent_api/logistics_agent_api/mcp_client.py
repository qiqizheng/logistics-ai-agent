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
        return await self._call_tool(
            "get_order_detail", {"order_no": order_no}, "订单查询失败"
        )

    async def get_shipment_detail(self, shipment_no: str) -> MCPToolResult:
        """通过 Streamable HTTP 调用提单 MCP。"""
        return await self._call_tool(
            "get_shipment_detail",
            {"shipment_no": shipment_no},
            "提单查询失败",
        )

    async def get_payment_voucher_detail(
        self, voucher_num: str
    ) -> MCPToolResult:
        """通过 Streamable HTTP 调用财务付款单 MCP。"""
        return await self._call_tool(
            "get_payment_voucher_detail",
            {"voucher_num": voucher_num},
            "付款单查询失败",
        )

    async def get_reconciliation_bill_detail(
        self, bill_num: str
    ) -> MCPToolResult:
        """通过 Streamable HTTP 调用财务对账单 MCP。"""
        return await self._call_tool(
            "get_reconciliation_bill_detail",
            {"bill_num": bill_num},
            "对账单查询失败",
        )

    async def _call_tool(
        self,
        tool_name: str,
        arguments: dict[str, str],
        fallback_error: str,
    ) -> MCPToolResult:
        async with Client(
            self.server_url,
            read_timeout_seconds=self.timeout_seconds,
        ) as client:
            response = await client.call_tool(tool_name, arguments)

        if response.is_error:
            message = "；".join(
                block.text
                for block in response.content
                if hasattr(block, "text") and block.text
            )
            return MCPToolResult(
                status="error",
                result=message or fallback_error,
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
