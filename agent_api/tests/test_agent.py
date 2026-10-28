"""千问工具调用与 MCP 编排测试。"""

import json
import unittest
from types import SimpleNamespace
from typing import Any

from logistics_agent_api.agent import AgentService
from logistics_agent_api.mcp_client import MCPToolResult


class FakeToolCall:
    def __init__(self, order_no: str) -> None:
        self.id = "call-1"
        self.function = SimpleNamespace(
            name="get_order_detail",
            arguments=json.dumps({"order_no": order_no}),
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
            "请确认订单号是否正确，或稍后重试。",
        )
        self.assertNotIn("客服电话", result.answer)
        self.assertEqual(result.tools[0]["status"], "error")


if __name__ == "__main__":
    unittest.main()
