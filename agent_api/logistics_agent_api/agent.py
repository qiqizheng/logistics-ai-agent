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

LOGISTICS_TOOLS: list[dict[str, Any]] = [
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_shipment_detail",
            "description": "根据提单号查询真实的提单操作状态。用户询问具体提单状态时必须调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "shipment_no": {
                        "type": "string",
                        "description": "提单号",
                    }
                },
                "required": ["shipment_no"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_payment_voucher_detail",
            "description": "根据付款单号查询真实的财务付款单状态。用户询问具体付款单状态时必须调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "voucher_num": {
                        "type": "string",
                        "description": "付款单号，例如 LD20261029010",
                    }
                },
                "required": ["voucher_num"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_reconciliation_bill_detail",
            "description": "根据对账单号查询真实的财务对账单状态。用户询问具体对账单状态时必须调用，不要调用付款单工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "bill_num": {
                        "type": "string",
                        "description": "对账单号，例如 OUT20260917001",
                    }
                },
                "required": ["bill_num"],
                "additionalProperties": False,
            },
        },
    },
]


@dataclass(frozen=True)
class AgentAnswer:
    answer: str
    tools: list[dict[str, object]]


class AgentService:
    def __init__(self, llm: LLMService, order_mcp: OrderMCPClient) -> None:
        self.llm = llm
        self.logistics_mcp = order_mcp

    async def answer(self, messages: list[MemoryMessage]) -> AgentAnswer:
        working_messages: list[dict[str, Any]] = list(messages)
        first_message = await self.llm.complete_chat(
            working_messages, tools=LOGISTICS_TOOLS
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
        failed_subject = ""
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

                if tool_call.function.name == "get_order_detail":
                    order_no = str(arguments.get("order_no", "")).strip()
                    failed_subject = f"订单 {order_no}".strip()
                    if not order_no:
                        result = MCPToolResult(
                            status="error", result="订单号不能为空"
                        )
                    else:
                        result = await self.logistics_mcp.get_order_detail(order_no)
                elif tool_call.function.name == "get_shipment_detail":
                    shipment_no = str(arguments.get("shipment_no", "")).strip()
                    failed_subject = f"提单 {shipment_no}".strip()
                    if not shipment_no:
                        result = MCPToolResult(
                            status="error", result="提单号不能为空"
                        )
                    else:
                        result = await self.logistics_mcp.get_shipment_detail(
                            shipment_no
                        )
                elif tool_call.function.name == "get_payment_voucher_detail":
                    voucher_num = str(arguments.get("voucher_num", "")).strip()
                    failed_subject = f"付款单 {voucher_num}".strip()
                    if not voucher_num:
                        result = MCPToolResult(
                            status="error", result="付款单号不能为空"
                        )
                    else:
                        result = (
                            await self.logistics_mcp.get_payment_voucher_detail(
                                voucher_num
                            )
                        )
                elif tool_call.function.name == "get_reconciliation_bill_detail":
                    bill_num = str(arguments.get("bill_num", "")).strip()
                    failed_subject = f"对账单 {bill_num}".strip()
                    if not bill_num:
                        result = MCPToolResult(
                            status="error", result="对账单号不能为空"
                        )
                    else:
                        result = (
                            await self.logistics_mcp.get_reconciliation_bill_detail(
                                bill_num
                            )
                        )
                else:
                    failed_subject = "工具"
                    result = MCPToolResult(
                        status="error",
                        result=f"不支持的工具：{tool_call.function.name}",
                    )
            except (json.JSONDecodeError, ValueError) as exc:
                result = MCPToolResult(status="error", result=str(exc))
                failed_subject = "工具"
            except Exception:
                logger.exception("物流 MCP 调用失败")
                result = MCPToolResult(
                    status="error", result="物流 MCP 服务暂时不可用"
                )

            if result.status == "error" and not failed_reason:
                failed_reason = str(result.result)

            traces.append(
                {
                    "name": tool_call.function.name,
                    "server": "物流业务 MCP Server",
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
                    f"{failed_subject} 查询失败：{failed_reason}。"
                    "请确认编号是否正确，或稍后重试。"
                ),
                tools=traces,
            )

        final_message = await self.llm.complete_chat(working_messages)
        answer = (final_message.content or "").strip()
        if not answer:
            raise RuntimeError("模型返回了空内容")
        return AgentAnswer(answer=answer, tools=traces)
