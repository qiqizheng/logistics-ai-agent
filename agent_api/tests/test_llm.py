"""千问调用参数测试。"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from logistics_agent_api.config import Settings
from logistics_agent_api.llm import LLMService


class LLMServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_qwen_chat_completions_receives_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(
                llm_api_key="test-dashscope-key",
                llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                llm_model="qwen-plus",
                llm_api_style="chat_completions",
                llm_max_output_tokens=800,
                llm_timeout_seconds=30,
                system_prompt="你是物流助手。",
                memory_max_messages=20,
                memory_db_path=Path(directory) / "memory.db",
                mcp_server_url="http://127.0.0.1:8001/mcp",
                mcp_timeout_seconds=15,
                api_host="127.0.0.1",
                api_port=8000,
                cors_origins=(),
            )

            create = AsyncMock(
                return_value=SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content="  千问回复  ")
                        )
                    ]
                )
            )
            client = MagicMock()
            client.chat.completions.create = create

            with patch(
                "logistics_agent_api.llm.AsyncOpenAI", return_value=client
            ) as client_factory:
                answer = await LLMService(settings).generate(
                    [
                        {"role": "user", "content": "上一问"},
                        {"role": "assistant", "content": "上一答"},
                        {"role": "user", "content": "本次问题"},
                    ]
                )

        self.assertEqual(answer, "千问回复")
        client_factory.assert_called_once_with(
            api_key="test-dashscope-key",
            timeout=30,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        call = create.await_args.kwargs
        self.assertEqual(call["model"], "qwen-plus")
        self.assertEqual(call["max_tokens"], 800)
        self.assertEqual(call["messages"][0], {
            "role": "system",
            "content": "你是物流助手。",
        })
        self.assertEqual(call["messages"][-1]["content"], "本次问题")


if __name__ == "__main__":
    unittest.main()
