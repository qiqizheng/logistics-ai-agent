"""SQLite Memory 测试。"""

import tempfile
import unittest
from pathlib import Path

from logistics_agent_api.memory import MemoryStore


class MemoryStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "memory.db"
        self.memory = MemoryStore(database_path)
        self.memory.initialize()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_exchange_is_persisted_in_order(self) -> None:
        self.memory.append_exchange("c1", "你好", "你好，有什么可以帮你？")
        self.memory.append_exchange("c1", "我刚才说了什么？", "你说了你好。")

        self.assertEqual(
            self.memory.get_all_messages("c1"),
            [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好，有什么可以帮你？"},
                {"role": "user", "content": "我刚才说了什么？"},
                {"role": "assistant", "content": "你说了你好。"},
            ],
        )

    def test_recent_messages_are_trimmed_but_keep_order(self) -> None:
        self.memory.append_exchange("c1", "问题一", "回答一")
        self.memory.append_exchange("c1", "问题二", "回答二")

        self.assertEqual(
            self.memory.get_recent_messages("c1", 2),
            [
                {"role": "user", "content": "问题二"},
                {"role": "assistant", "content": "回答二"},
            ],
        )

    def test_delete_conversation_cascades_messages(self) -> None:
        self.memory.append_exchange("c1", "问题", "回答")

        self.assertTrue(self.memory.delete_conversation("c1"))
        self.assertEqual(self.memory.get_all_messages("c1"), [])

