"""MCP 服务注册测试。"""

import unittest

from mcp import Client

from logistics_mcp.server import mcp


class ServerRegistrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_order_detail_is_registered(self) -> None:
        async with Client(mcp) as client:
            result = await client.list_tools()

        tools = {tool.name: tool for tool in result.tools}
        self.assertIn("get_order_detail", tools)
        self.assertEqual(
            set(tools["get_order_detail"].input_schema["properties"]),
            {"order_no"},
        )


if __name__ == "__main__":
    unittest.main()

