"""FastAPI 与 Memory 集成测试。"""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from logistics_agent_api.agent import AgentAnswer
from logistics_agent_api.config import Settings
from logistics_agent_api.main import create_app
from logistics_agent_api.memory import MemoryMessage


class FakeAgentService:
    def __init__(self) -> None:
        self.calls: list[list[MemoryMessage]] = []

    async def answer(self, messages: list[MemoryMessage]) -> AgentAnswer:
        self.calls.append(messages)
        return AgentAnswer(
            answer=f"已收到：{messages[-1]['content']}", tools=[]
        )


class ApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        settings = Settings(
            llm_api_key="test-key",
            llm_base_url=None,
            llm_model="test-model",
            llm_api_style="responses",
            llm_max_output_tokens=100,
            llm_timeout_seconds=10,
            system_prompt="test",
            memory_max_messages=20,
            memory_db_path=Path(self.temporary_directory.name) / "memory.db",
            mcp_server_url="http://127.0.0.1:8001/mcp",
            mcp_timeout_seconds=15,
            api_host="127.0.0.1",
            api_port=8000,
            cors_origins=("http://localhost:5173",),
        )
        self.agent = FakeAgentService()
        self.client_context = TestClient(
            create_app(settings, agent_service=self.agent)
        )
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.temporary_directory.cleanup()

    def test_chat_response_matches_vue_contract_and_remembers_history(self) -> None:
        first = self.client.post(
            "/chat",
            json={"message": "你好", "conversation_id": "conversation-1"},
        )
        second = self.client.post(
            "/chat",
            json={"message": "继续", "conversation_id": "conversation-1"},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(
            first.json(),
            {
                "answer": "已收到：你好",
                "conversation_id": "conversation-1",
                "tools": [],
            },
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            self.agent.calls[1],
            [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "已收到：你好"},
                {"role": "user", "content": "继续"},
            ],
        )

        history = self.client.get(
            "/conversations/conversation-1/messages"
        )
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()), 4)

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["memory"], "sqlite")
