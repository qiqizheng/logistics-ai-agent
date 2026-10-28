"""订单查询工具的领域逻辑。"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, Field

from logistics_mcp.database import create_connection


ORDER_STATUS_NAMES: Final[dict[int, str]] = {
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


class OrderNotFoundError(LookupError):
    """订单号在报价表中不存在。"""


class OrderDetail(BaseModel):
    """订单状态查询结果。"""

    programme_num: str = Field(description="订单号")
    examine_status: int = Field(description="订单状态码")
    status_text: str = Field(description="订单状态中文名称")


def status_name(status_code: int) -> str:
    """将数据库状态码转换为中文状态。"""
    return ORDER_STATUS_NAMES.get(status_code, f"未知状态({status_code})")


def query_order_detail(order_no: str) -> OrderDetail:
    """按订单号查询订单状态。"""
    normalized_order_no = order_no.strip()
    if not normalized_order_no:
        raise ValueError("订单号不能为空")

    sql = """
        SELECT programme_num, examine_status
        FROM tb_freight_quotation
        WHERE programme_num = %s
        LIMIT 1
    """

    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, (normalized_order_no,))
            row = cursor.fetchone()

    if row is None:
        raise OrderNotFoundError(f"未找到订单：{normalized_order_no}")

    status_code = int(row["examine_status"])
    return OrderDetail(
        programme_num=str(row["programme_num"]),
        examine_status=status_code,
        status_text=status_name(status_code),
    )

