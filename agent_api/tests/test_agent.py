"""千问工具调用与 MCP 编排测试。"""

import json
import unittest
from types import SimpleNamespace
from typing import Any

from logistics_agent_api.agent import AgentService
from logistics_agent_api.mcp_client import MCPToolResult


class FakeToolCall:
    def __init__(
        self,
        identifier: str,
        tool_name: str = "get_order_detail",
        argument_name: str = "order_no",
    ) -> None:
        self.id = "call-1"
        self.function = SimpleNamespace(
            name=tool_name,
            arguments=json.dumps({argument_name: identifier}),
        )

    def model_dump(self, **kwargs: object) -> dict[str, object]:
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.function.name,
                "arguments": self.function.arguments,
            },
        }


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[tuple[list[dict[str, Any]], object]] = []

    async def complete_chat(
        self,
        messages: list[dict[str, Any]],
        tools: object = None,
    ) -> object:
        self.calls.append((messages, tools))
        if len(self.calls) == 1:
            return SimpleNamespace(
                content="", tool_calls=[FakeToolCall("JFK24050029")]
            )
        return SimpleNamespace(
            content="订单 JFK24050029 当前状态为运输中。",
            tool_calls=None,
        )


class FakeOrderMCP:
    def __init__(self) -> None:
        self.order_numbers: list[str] = []

    async def get_order_detail(self, order_no: str) -> MCPToolResult:
        self.order_numbers.append(order_no)
        return MCPToolResult(
            status="success",
            result={
                "programme_num": order_no,
                "examine_status": 6,
                "status_text": "运输中",
            },
        )


class FailingOrderMCP:
    async def get_order_detail(self, order_no: str) -> MCPToolResult:
        return MCPToolResult(status="error", result="未找到该订单")


class FakeShipmentLLM(FakeLLM):
    async def complete_chat(
        self,
        messages: list[dict[str, Any]],
        tools: object = None,
    ) -> object:
        self.calls.append((messages, tools))
        if len(self.calls) == 1:
            return SimpleNamespace(
                content="",
                tool_calls=[
                    FakeToolCall(
                        "BL20261030001",
                        tool_name="get_shipment_detail",
                        argument_name="shipment_no",
                    )
                ],
            )
        return SimpleNamespace(
            content="提单 BL20261030001 当前状态为已绑干线。",
            tool_calls=None,
        )


class FakeShipmentMCP:
    def __init__(self) -> None:
        self.shipment_numbers: list[str] = []

    async def get_shipment_detail(self, shipment_no: str) -> MCPToolResult:
        self.shipment_numbers.append(shipment_no)
        return MCPToolResult(
            status="success",
            result={
                "shipment_no": shipment_no,
                "operating_status": 3,
                "status_text": "已绑干线",
            },
        )


class FakeFinanceLLM(FakeLLM):
    async def complete_chat(
        self,
        messages: list[dict[str, Any]],
        tools: object = None,
    ) -> object:
        self.calls.append((messages, tools))
        if len(self.calls) == 1:
            return SimpleNamespace(
                content="",
                tool_calls=[
                    FakeToolCall(
                        "LD20261029010",
                        tool_name="get_payment_voucher_detail",
                        argument_name="voucher_num",
                    )
                ],
            )
        return SimpleNamespace(
            content="付款单 LD20261029010 当前状态为审核。",
            tool_calls=None,
        )


class FakeFinanceMCP:
    def __init__(self) -> None:
        self.voucher_numbers: list[str] = []

    async def get_payment_voucher_detail(
        self, voucher_num: str
    ) -> MCPToolResult:
        self.voucher_numbers.append(voucher_num)
        return MCPToolResult(
            status="success",
            result={
                "voucher_num": voucher_num,
                "status": 200,
                "status_text": "审核",
            },
        )


class FakeReconciliationBillLLM(FakeLLM):
    async def complete_chat(
        self,
        messages: list[dict[str, Any]],
        tools: object = None,
    ) -> object:
        self.calls.append((messages, tools))
        if len(self.calls) == 1:
            return SimpleNamespace(
                content="",
                tool_calls=[
                    FakeToolCall(
                        "OUT20260917001",
                        tool_name="get_reconciliation_bill_detail",
                        argument_name="bill_num",
                    )
                ],
            )
        return SimpleNamespace(
            content="对账单 OUT20260917001 当前状态为新建。",
            tool_calls=None,
        )


class FakeReconciliationBillMCP:
    def __init__(self) -> None:
        self.bill_numbers: list[str] = []

    async def get_reconciliation_bill_detail(
        self, bill_num: str
    ) -> MCPToolResult:
        self.bill_numbers.append(bill_num)
        return MCPToolResult(
            status="success",
            result={
                "bill_num": bill_num,
                "status": 100,
                "status_text": "新建",
            },
        )


class AgentServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_order_tool_result_is_returned_to_qwen_and_frontend(self) -> None:
        llm = FakeLLM()
        order_mcp = FakeOrderMCP()
        agent = AgentService(llm, order_mcp)  # type: ignore[arg-type]

        result = await agent.answer(
            [{"role": "user", "content": "查询 JFK24050029 的状态"}]
        )

        self.assertEqual(order_mcp.order_numbers, ["JFK24050029"])
        self.assertEqual(
            result.answer, "订单 JFK24050029 当前状态为运输中。"
        )
        self.assertEqual(result.tools[0]["name"], "get_order_detail")
        self.assertEqual(result.tools[0]["status"], "success")
        self.assertEqual(
            result.tools[0]["result"],
            {
                "programme_num": "JFK24050029",
                "examine_status": 6,
                "status_text": "运输中",
            },
        )

        second_messages = llm.calls[1][0]
        self.assertEqual(second_messages[-1]["role"], "tool")
        self.assertIn("运输中", second_messages[-1]["content"])

    async def test_mcp_failure_returns_fixed_answer_without_llm_invention(self) -> None:
        llm = FakeLLM()
        agent = AgentService(llm, FailingOrderMCP())  # type: ignore[arg-type]

        result = await agent.answer(
            [{"role": "user", "content": "查询 JFK24050029 的状态"}]
        )

        self.assertEqual(len(llm.calls), 1)
        self.assertEqual(
            result.answer,
            "订单 JFK24050029 查询失败：未找到该订单。"
            "请确认编号是否正确，或稍后重试。",
        )
        self.assertNotIn("客服电话", result.answer)
        self.assertEqual(result.tools[0]["status"], "error")

    async def test_shipment_tool_result_is_returned_to_qwen_and_frontend(self) -> None:
        llm = FakeShipmentLLM()
        shipment_mcp = FakeShipmentMCP()
        agent = AgentService(llm, shipment_mcp)  # type: ignore[arg-type]

        result = await agent.answer(
            [{"role": "user", "content": "查询提单 BL20261030001 的状态"}]
        )

        self.assertEqual(shipment_mcp.shipment_numbers, ["BL20261030001"])
        self.assertEqual(
            result.answer, "提单 BL20261030001 当前状态为已绑干线。"
        )
        self.assertEqual(result.tools[0]["name"], "get_shipment_detail")
        self.assertEqual(result.tools[0]["status"], "success")
        self.assertEqual(
            result.tools[0]["result"],
            {
                "shipment_no": "BL20261030001",
                "operating_status": 3,
                "status_text": "已绑干线",
            },
        )

        declared_tools = llm.calls[0][1]
        tool_names = {
            tool["function"]["name"] for tool in declared_tools  # type: ignore[union-attr]
        }
        self.assertEqual(
            tool_names,
            {
                "get_order_detail",
                "get_shipment_detail",
                "get_payment_voucher_detail",
                "get_reconciliation_bill_detail",
            },
        )

    async def test_payment_voucher_tool_result_is_returned_to_qwen(self) -> None:
        llm = FakeFinanceLLM()
        finance_mcp = FakeFinanceMCP()
        agent = AgentService(llm, finance_mcp)  # type: ignore[arg-type]

        result = await agent.answer(
            [{"role": "user", "content": "查询付款单 LD20261029010 的状态"}]
        )

        self.assertEqual(finance_mcp.voucher_numbers, ["LD20261029010"])
        self.assertEqual(
            result.answer, "付款单 LD20261029010 当前状态为审核。"
        )
        self.assertEqual(
            result.tools[0]["name"], "get_payment_voucher_detail"
        )
        self.assertEqual(result.tools[0]["status"], "success")
        self.assertEqual(
            result.tools[0]["result"],
            {
                "voucher_num": "LD20261029010",
                "status": 200,
                "status_text": "审核",
            },
        )

    async def test_reconciliation_bill_tool_result_is_returned_to_qwen(
        self,
    ) -> None:
        llm = FakeReconciliationBillLLM()
        bill_mcp = FakeReconciliationBillMCP()
        agent = AgentService(llm, bill_mcp)  # type: ignore[arg-type]

        result = await agent.answer(
            [{"role": "user", "content": "查询对账单 OUT20260917001 的状态"}]
        )

        self.assertEqual(bill_mcp.bill_numbers, ["OUT20260917001"])
        self.assertEqual(
            result.answer, "对账单 OUT20260917001 当前状态为新建。"
        )
        self.assertEqual(
            result.tools[0]["name"], "get_reconciliation_bill_detail"
        )
        self.assertEqual(result.tools[0]["status"], "success")
        self.assertEqual(
            result.tools[0]["result"],
            {
                "bill_num": "OUT20260917001",
                "status": 100,
                "status_text": "新建",
            },
        )


if __name__ == "__main__":
    unittest.main()
