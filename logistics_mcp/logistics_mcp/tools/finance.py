"""财务付款单状态查询工具的领域逻辑。"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, Field

from logistics_mcp.database import create_connection


PAYMENT_VOUCHER_STATUS_NAMES: Final[dict[int, str]] = {
    100: "新建",
    200: "审核",
    300: "记账",
    400: "作废",
}

RECONCILIATION_BILL_STATUS_NAMES: Final[dict[int, str]] = {
    100: "新建",
    200: "审核",
    300: "记账",
}


class PaymentVoucherNotFoundError(LookupError):
    """付款单号在财务凭证表中不存在。"""


class ReconciliationBillNotFoundError(LookupError):
    """对账单号在财务对账单表中不存在。"""


class PaymentVoucherDetail(BaseModel):
    """付款单状态查询结果。"""

    voucher_num: str = Field(description="付款单号")
    status: int = Field(description="付款单状态码")
    status_text: str = Field(description="付款单状态中文名称")


class ReconciliationBillDetail(BaseModel):
    """对账单状态查询结果。"""

    bill_num: str = Field(description="对账单号")
    status: int = Field(description="对账单状态码")
    status_text: str = Field(description="对账单状态中文名称")


def payment_voucher_status_name(status_code: int) -> str:
    """将付款单状态码转换为中文状态。"""
    return PAYMENT_VOUCHER_STATUS_NAMES.get(
        status_code, f"未知状态({status_code})"
    )


def reconciliation_bill_status_name(status_code: int) -> str:
    """将对账单状态码转换为中文状态。"""
    return RECONCILIATION_BILL_STATUS_NAMES.get(
        status_code, f"未知状态({status_code})"
    )


def query_payment_voucher_detail(voucher_num: str) -> PaymentVoucherDetail:
    """按付款单号查询付款单状态。"""
    normalized_voucher_num = voucher_num.strip()
    if not normalized_voucher_num:
        raise ValueError("付款单号不能为空")

    sql = """
        SELECT voucher_num, status
        FROM tb_fee_voucher
        WHERE voucher_num = %s
        LIMIT 1
    """

    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, (normalized_voucher_num,))
            row = cursor.fetchone()

    if row is None:
        raise PaymentVoucherNotFoundError(
            f"未找到付款单：{normalized_voucher_num}"
        )

    status_code = int(row["status"])
    return PaymentVoucherDetail(
        voucher_num=str(row["voucher_num"]),
        status=status_code,
        status_text=payment_voucher_status_name(status_code),
    )


def query_reconciliation_bill_detail(
    bill_num: str,
) -> ReconciliationBillDetail:
    """按对账单号查询对账单状态。"""
    normalized_bill_num = bill_num.strip()
    if not normalized_bill_num:
        raise ValueError("对账单号不能为空")

    sql = """
        SELECT bill_num, status
        FROM tb_fee_bill
        WHERE bill_num = %s
        LIMIT 1
    """

    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, (normalized_bill_num,))
            row = cursor.fetchone()

    if row is None:
        raise ReconciliationBillNotFoundError(
            f"未找到对账单：{normalized_bill_num}"
        )

    status_code = int(row["status"])
    return ReconciliationBillDetail(
        bill_num=str(row["bill_num"]),
        status=status_code,
        status_text=reconciliation_bill_status_name(status_code),
    )
