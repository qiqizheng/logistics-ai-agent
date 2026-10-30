"""提单查询工具的领域逻辑。"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, Field

from logistics_mcp.database import create_connection


SHIPMENT_STATUS_NAMES: Final[dict[int, str]] = {
    1: "待流转干线",
    2: "待绑干线",
    3: "已绑干线",
    4: "待更资料",
    5: "已更资料",
    6: "资料归档",
}


class ShipmentNotFoundError(LookupError):
    """提单号在提单表中不存在。"""


class ShipmentDetail(BaseModel):
    """提单状态查询结果。"""

    shipment_no: str = Field(description="提单号")
    operating_status: int = Field(description="提单操作状态码")
    status_text: str = Field(description="提单状态中文名称")


def shipment_status_name(status_code: int) -> str:
    """将数据库操作状态码转换为中文状态。"""
    return SHIPMENT_STATUS_NAMES.get(status_code, f"未知状态({status_code})")


def query_shipment_detail(shipment_no: str) -> ShipmentDetail:
    """按提单号查询提单状态。"""
    normalized_shipment_no = shipment_no.strip()
    if not normalized_shipment_no:
        raise ValueError("提单号不能为空")

    sql = """
        SELECT shipment_code AS shipment_no, operating_status
        FROM tb_shipment
        WHERE shipment_code = %s
        LIMIT 1
    """

    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, (normalized_shipment_no,))
            row = cursor.fetchone()

    if row is None:
        raise ShipmentNotFoundError(f"未找到提单：{normalized_shipment_no}")

    status_code = int(row["operating_status"])
    return ShipmentDetail(
        shipment_no=str(row["shipment_no"]),
        operating_status=status_code,
        status_text=shipment_status_name(status_code),
    )
