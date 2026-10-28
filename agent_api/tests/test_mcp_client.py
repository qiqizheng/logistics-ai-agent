"""MCP 客户端参数与结果测试。"""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from logistics_agent_api.mcp_client import OrderMCPClient


class FakeClientContext:
    def __init__(self) -> None:
        self.call_tool = AsyncMock(
            return_value=SimpleNamespace(
                is_error=False,
                structured_content={
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


if __name__ == "__main__":
    unittest.main()

