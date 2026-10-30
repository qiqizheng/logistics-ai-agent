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

    async def test_get_shipment_detail_is_registered(self) -> None:
        async with Client(mcp) as client:
            result = await client.list_tools()

        tools = {tool.name: tool for tool in result.tools}
        self.assertIn("get_shipment_detail", tools)
        self.assertEqual(
            set(tools["get_shipment_detail"].input_schema["properties"]),
            {"shipment_no"},
        )

    async def test_get_payment_voucher_detail_is_registered(self) -> None:
        async with Client(mcp) as client:
            result = await client.list_tools()

        tools = {tool.name: tool for tool in result.tools}
        self.assertIn("get_payment_voucher_detail", tools)
        self.assertEqual(
            set(tools["get_payment_voucher_detail"].input_schema["properties"]),
            {"voucher_num"},
        )

    async def test_get_reconciliation_bill_detail_is_registered(self) -> None:
        async with Client(mcp) as client:
            result = await client.list_tools()

        tools = {tool.name: tool for tool in result.tools}
        self.assertIn("get_reconciliation_bill_detail", tools)
        self.assertEqual(
            set(
                tools["get_reconciliation_bill_detail"].input_schema[
                    "properties"
                ]
            ),
            {"bill_num"},
        )


if __name__ == "__main__":
    unittest.main()
