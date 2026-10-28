"""LLM 调用封装。"""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from logistics_agent_api.config import Settings
from logistics_agent_api.memory import MemoryMessage


class LLMConfigurationError(RuntimeError):
    """LLM 必需配置缺失。"""


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: AsyncOpenAI | None = None

    def _create_client(self) -> AsyncOpenAI:
        if not self.settings.llm_api_key:
            raise LLMConfigurationError("尚未配置 DASHSCOPE_API_KEY")
        if not self.settings.llm_model:
            raise LLMConfigurationError("尚未配置 LLM_MODEL")

        kwargs: dict[str, object] = {
            "api_key": self.settings.llm_api_key,
            "timeout": self.settings.llm_timeout_seconds,
        }
        if self.settings.llm_base_url:
            kwargs["base_url"] = self.settings.llm_base_url
        if self._client is None:
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def complete_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        """调用千问 Chat Completions，并保留可能返回的工具调用。"""
        if self.settings.llm_api_style != "chat_completions":
            raise LLMConfigurationError(
                "MCP 工具调用要求 LLM_API_STYLE=chat_completions"
            )

        client = self._create_client()
        chat_messages = [
            {"role": "system", "content": self.settings.system_prompt},
            *messages,
        ]
        request: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": chat_messages,
            "max_tokens": self.settings.llm_max_output_tokens,
        }
        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"

        completion = await client.chat.completions.create(**request)
        return completion.choices[0].message

    async def generate(self, messages: list[MemoryMessage]) -> str:
        if self.settings.llm_api_style == "chat_completions":
            message = await self.complete_chat(list(messages))
            answer = message.content or ""
        else:
            client = self._create_client()
            response = await client.responses.create(
                model=self.settings.llm_model,
                instructions=self.settings.system_prompt,
                input=messages,  # type: ignore[arg-type]
                max_output_tokens=self.settings.llm_max_output_tokens,
                store=False,
            )
            answer = response.output_text

        answer = answer.strip()
        if not answer:
            raise RuntimeError("模型返回了空内容")
        return answer
