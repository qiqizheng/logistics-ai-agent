"""千问 Function Calling 与 MCP 工具编排。"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from logistics_agent_api.llm import LLMService
from logistics_agent_api.mcp_client import MCPToolResult, OrderMCPClient
from logistics_agent_api.memory import MemoryMessage


logger = logging.getLogger(__name__)

ORDER_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_order_detail",
            "description": "根据订单号查询物流订单的真实状态。用户询问具体订单状态时必须调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {
                        "type": "string",
                        "description": "订单号，例如 JFK24050029",
                    }
                },
                "required": ["order_no"],
                "additionalProperties": False,
            },
        },
    }
]


@dataclass(frozen=True)
class AgentAnswer:
    answer: str
    tools: list[dict[str, object]]


class AgentService:
    def __init__(self, llm: LLMService, order_mcp: OrderMCPClient) -> None:
        self.llm = llm
        self.order_mcp = order_mcp

    async def answer(self, messages: list[MemoryMessage]) -> AgentAnswer:
        working_messages: list[dict[str, Any]] = list(messages)
        first_message = await self.llm.complete_chat(
            working_messages, tools=ORDER_TOOLS
        )
        tool_calls = first_message.tool_calls or []

        if not tool_calls:
            answer = (first_message.content or "").strip()
            if not answer:
                raise RuntimeError("模型返回了空内容")
            return AgentAnswer(answer=answer, tools=[])

        working_messages.append(
            {
                "role": "assistant",
                "content": first_message.content or "",
                "tool_calls": [
                    tool_call.model_dump(exclude_none=True)
                    for tool_call in tool_calls
                ],
            }
        )

        traces: list[dict[str, object]] = []
        failed_order_no = ""
        failed_reason = ""
        for tool_call in tool_calls:
            started_at = time.perf_counter()
            arguments: dict[str, Any] = {}
            result = MCPToolResult(status="error", result="不支持的工具")

            try:
                parsed = json.loads(tool_call.function.arguments or "{}")
                if not isinstance(parsed, dict):
                    raise ValueError("工具参数必须是 JSON 对象")
                arguments = parsed

                if tool_call.function.name != "get_order_detail":
                    result = MCPToolResult(
                        status="error",
                        result=f"不支持的工具：{tool_call.function.name}",
                    )
                else:
                    order_no = str(arguments.get("order_no", "")).strip()
                    if not order_no:
                        result = MCPToolResult(
                            status="error", result="订单号不能为空"
                        )
                    else:
                        result = await self.order_mcp.get_order_detail(order_no)
                        if result.status == "error":
                            failed_order_no = order_no
                            failed_reason = str(result.result)
            except (json.JSONDecodeError, ValueError) as exc:
                result = MCPToolResult(status="error", result=str(exc))
            except Exception:
                logger.exception("订单 MCP 调用失败")
                result = MCPToolResult(
                    status="error", result="订单 MCP 服务暂时不可用"
                )

            traces.append(
                {
                    "name": tool_call.function.name,
                    "server": "订单 MCP Server",
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000
                    ),
                    "status": result.status,
                    "arguments": arguments,
                    "result": result.result,
                }
            )
            working_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        result.result, ensure_ascii=False
                    ),
                }
            )

        if failed_reason:
            return AgentAnswer(
                answer=(
                    f"订单 {failed_order_no} 查询失败：{failed_reason}。"
                    "请确认订单号是否正确，或稍后重试。"
                ),
                tools=traces,
            )

        final_message = await self.llm.complete_chat(working_messages)
        answer = (final_message.content or "").strip()
        if not answer:
            raise RuntimeError("模型返回了空内容")
        return AgentAnswer(answer=answer, tools=traces)
