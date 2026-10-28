"""订单状态映射的单元测试。"""

import unittest
from unittest.mock import patch

from logistics_mcp.tools.order import (
    ORDER_STATUS_NAMES,
    OrderNotFoundError,
    query_order_detail,
    status_name,
)


class FakeCursor:
    def __init__(self, row: dict[str, object] | None) -> None:
        self.row = row
        self.sql = ""
        self.params: tuple[str, ...] = ()

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[str, ...]) -> None:
        self.sql = sql
        self.params = params

    def fetchone(self) -> dict[str, object] | None:
        return self.row


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self.fake_cursor


class OrderStatusTest(unittest.TestCase):
    def test_all_known_statuses(self) -> None:
        expected = {
            0: "新建",
            1: "审核中",
            2: "通过待流转",
            3: "已确定流转",
            4: "审核未通过",
            5: "作废",
            6: "运输中",
            7: "已完结",
            8: "流转异常",
            9: "订单异常",
            10: "已申请流转",
        }
        self.assertEqual(ORDER_STATUS_NAMES, expected)

    def test_unknown_status_is_preserved(self) -> None:
        self.assertEqual(status_name(99), "未知状态(99)")

    def test_query_uses_parameterized_order_number(self) -> None:
        cursor = FakeCursor(
            {"programme_num": "OD202410180026", "examine_status": 6}
        )
        connection = FakeConnection(cursor)

        with patch(
            "logistics_mcp.tools.order.create_connection", return_value=connection
        ):
            result = query_order_detail("  OD202410180026  ")

        self.assertIn("WHERE programme_num = %s", cursor.sql)
        self.assertEqual(cursor.params, ("OD202410180026",))
        self.assertEqual(result.programme_num, "OD202410180026")
        self.assertEqual(result.examine_status, 6)
        self.assertEqual(result.status_text, "运输中")

    def test_missing_order_raises_a_clear_error(self) -> None:
        connection = FakeConnection(FakeCursor(None))

        with patch(
            "logistics_mcp.tools.order.create_connection", return_value=connection
        ):
            with self.assertRaisesRegex(OrderNotFoundError, "OD-NOT-FOUND"):
                query_order_detail("OD-NOT-FOUND")


if __name__ == "__main__":
    unittest.main()
