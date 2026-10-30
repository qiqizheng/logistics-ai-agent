"""应用配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    llm_api_key: str
    llm_base_url: str | None
    llm_model: str
    llm_api_style: Literal["responses", "chat_completions"]
    llm_max_output_tokens: int
    llm_timeout_seconds: float
    system_prompt: str
    memory_max_messages: int
    memory_db_path: Path
    mcp_server_url: str
    mcp_timeout_seconds: float
    api_host: str
    api_port: int
    cors_origins: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> "Settings":
        api_style = os.getenv("LLM_API_STYLE", "chat_completions").strip()
        if api_style not in {"responses", "chat_completions"}:
            raise ValueError(
                "LLM_API_STYLE 只能是 responses 或 chat_completions"
            )

        database_path = Path(os.getenv("MEMORY_DB_PATH", "data/memory.db"))
        if not database_path.is_absolute():
            database_path = PROJECT_DIR / database_path

        origins = tuple(
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        )

        max_messages = int(os.getenv("MEMORY_MAX_MESSAGES", "20"))
        if max_messages < 0:
            raise ValueError("MEMORY_MAX_MESSAGES 不能小于 0")

        return cls(
            llm_api_key=(
                os.getenv("DASHSCOPE_API_KEY", "").strip()
                or os.getenv("LLM_API_KEY", "").strip()
            ),
            llm_base_url=os.getenv(
                "LLM_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ).strip()
            or None,
            llm_model=os.getenv("LLM_MODEL", "qwen-plus").strip(),
            llm_api_style=cast(
                Literal["responses", "chat_completions"], api_style
            ),
            llm_max_output_tokens=int(
                os.getenv("LLM_MAX_OUTPUT_TOKENS", "1200")
            ),
            llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
            system_prompt=os.getenv(
                "SYSTEM_PROMPT",
                "你是运智物流助手。请用简洁、准确的中文回答物流业务问题。"
                "查询具体订单号时必须调用 get_order_detail；查询具体提单号时"
                "必须调用 get_shipment_detail；查询具体付款单号时必须调用 "
                "get_payment_voucher_detail；查询具体对账单号时必须调用 "
                "get_reconciliation_bill_detail。只能依据工具结果回答；工具失败或"
                "没有数据时应如实说明，严禁编造状态、官网、客服电话或其他业务信息。",
            ),
            memory_max_messages=max_messages,
            memory_db_path=database_path,
            mcp_server_url=os.getenv(
                "MCP_SERVER_URL", "http://127.0.0.1:8001/mcp"
            ).strip(),
            mcp_timeout_seconds=float(os.getenv("MCP_TIMEOUT_SECONDS", "15")),
            api_host=os.getenv("API_HOST", "127.0.0.1"),
            api_port=int(os.getenv("API_PORT", "8000")),
            cors_origins=origins,
        )
