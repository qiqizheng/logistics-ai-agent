"""MCP 客户端参数与结果测试。"""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from logistics_agent_api.mcp_client import OrderMCPClient


class FakeClientContext:
    def __init__(self, structured_content: dict[str, object] | None = None) -> None:
        self.call_tool = AsyncMock(
            return_value=SimpleNamespace(
                is_error=False,
                structured_content=structured_content
                or {
                    "programme_num": "JFK24050029",
                    "examine_status": 0,
                    "status_text": "新建",
                },
                content=[],
            )
        )

    async def __aenter__(self) -> "FakeClientContext":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class MCPClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_uses_supported_read_timeout_argument(self) -> None:
        context = FakeClientContext()
        with patch(
            "logistics_agent_api.mcp_client.Client", return_value=context
        ) as client_factory:
            result = await OrderMCPClient(
                "http://127.0.0.1:8001/mcp", timeout_seconds=15
            ).get_order_detail("JFK24050029")

        client_factory.assert_called_once_with(
            "http://127.0.0.1:8001/mcp",
            read_timeout_seconds=15,
        )
        context.call_tool.assert_awaited_once_with(
            "get_order_detail", {"order_no": "JFK24050029"}
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(result.result["status_text"], "新建")

    async def test_calls_shipment_tool(self) -> None:
        context = FakeClientContext(
            {
                "shipment_no": "BL20261030001",
                "operating_status": 3,
                "status_text": "已绑干线",
            }
        )
        with patch(
            "logistics_agent_api.mcp_client.Client", return_value=context
        ):
            result = await OrderMCPClient(
                "http://127.0.0.1:8001/mcp", timeout_seconds=15
            ).get_shipment_detail("BL20261030001")

        context.call_tool.assert_awaited_once_with(
            "get_shipment_detail", {"shipment_no": "BL20261030001"}
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(result.result["status_text"], "已绑干线")

    async def test_calls_payment_voucher_tool(self) -> None:
        context = FakeClientContext(
            {
                "voucher_num": "LD20261029010",
                "status": 200,
                "status_text": "审核",
            }
        )
        with patch(
            "logistics_agent_api.mcp_client.Client", return_value=context
        ):
            result = await OrderMCPClient(
                "http://127.0.0.1:8001/mcp", timeout_seconds=15
            ).get_payment_voucher_detail("LD20261029010")

        context.call_tool.assert_awaited_once_with(
            "get_payment_voucher_detail", {"voucher_num": "LD20261029010"}
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(result.result["status_text"], "审核")

    async def test_calls_reconciliation_bill_tool(self) -> None:
        context = FakeClientContext(
            {
                "bill_num": "OUT20260917001",
                "status": 300,
                "status_text": "记账",
            }
        )
        with patch(
            "logistics_agent_api.mcp_client.Client", return_value=context
        ):
            result = await OrderMCPClient(
                "http://127.0.0.1:8001/mcp", timeout_seconds=15
            ).get_reconciliation_bill_detail("OUT20260917001")

        context.call_tool.assert_awaited_once_with(
            "get_reconciliation_bill_detail", {"bill_num": "OUT20260917001"}
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(result.result["status_text"], "记账")


if __name__ == "__main__":
    unittest.main()
