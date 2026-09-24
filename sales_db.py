"""销售数据的只读查询与校验。

所有 SQL 都在本模块中固定生成：值参数使用 SQLite 参数绑定，动态分组字段必须
来自白名单。MCP 层只负责暴露这些函数，不接受任意 SQL。
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterator


PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "data" / "sales_demo.db"

ALLOWED_REGIONS = ("华东", "华南", "华北")
PRODUCTS = {
    "P-100": "星云分析终端",
    "P-200": "远航协作套件",
    "P-300": "清岚服务平台",
}
GROUP_FIELDS = {
    "month": "month",
    "region": "region",
    "product": "product_code",
}
MAX_RESULT_ROWS = 50
MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class RequestValidationError(ValueError):
    """表示调用参数不符合本 Demo 的明确查询范围。"""


def _money(cents: int) -> dict[str, Any]:
    """同时返回精确整数分和便于阅读的元字符串。"""

    return {
        "sales_amount_cents": cents,
        "sales_amount_yuan": f"{Decimal(cents) / Decimal(100):.2f}",
        "currency": "CNY",
    }


@contextmanager
def readonly_connection() -> Iterator[sqlite3.Connection]:
    """以 SQLite 只读模式连接，防止查询进程意外修改模拟数据库。"""

    if not DB_PATH.exists():
        raise RuntimeError("模拟数据库不存在，请先运行 init_db.py。")
    database_uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    connection = sqlite3.connect(database_uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def _validate_month(month: str | None) -> None:
    if month is not None and not MONTH_PATTERN.fullmatch(month):
        raise RequestValidationError("月份必须使用 YYYY-MM 格式，例如 2026-08。")


def _validate_filters(region: str | None, product: str | None) -> None:
    if region is not None and region not in ALLOWED_REGIONS:
        raise RequestValidationError(
            f"不支持的区域：{region}。可用区域：{', '.join(ALLOWED_REGIONS)}。"
        )
    if product is not None and product not in PRODUCTS:
        raise RequestValidationError(
            f"不支持的产品编号：{product}。可用产品：{', '.join(PRODUCTS)}。"
        )


def _validate_group_by(group_by: list[str]) -> list[str]: # 判断group_by是否有效
    if len(group_by) != len(set(group_by)):
        raise RequestValidationError("分组字段不能重复。")
    invalid = [item for item in group_by if item not in GROUP_FIELDS]
    if invalid:
        raise RequestValidationError(
            "不支持的分组字段："
            + ", ".join(invalid)
            + "。只允许 month、region、product。"
        )
    return group_by


def _where_clause(
    month: str | None, region: str | None, product: str | None
) -> tuple[str, list[str]]:
    clauses: list[str] = []
    parameters: list[str] = []
    for column, value in (
        ("month", month),
        ("region", region),
        ("product_code", product),
    ):
        if value is not None:
            clauses.append(f"{column} = ?")
            parameters.append(value)
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), parameters


def _product_payload(product_code: str) -> dict[str, str]:
    return {
        "product_code": product_code,
        "product_name": PRODUCTS[product_code],
    }


def get_data_description() -> dict[str, Any]:
    """从数据库读取实际月份范围，并返回固定的数据字典。"""

    with readonly_connection() as connection:
        months = [
            row["month"]
            for row in connection.execute(
                "SELECT DISTINCT month FROM sales_records ORDER BY month"
            ).fetchall()
        ]
    return {
        "status": "ok",
        "data_classification": "虚构模拟数据",
        "dataset": "销售数据问数 MCP Demo",
        "grain": "每月 × 区域 × 产品一条汇总记录",
        "amount_definition": "销售额为模拟含税销售额；数据库按人民币分存储，接口同时返回元字符串。",
        "available_months": months,
        "available_regions": list(ALLOWED_REGIONS),
        "available_products": [
            {"product_code": code, "product_name": name}
            for code, name in PRODUCTS.items()
        ],
        "fields": {
            "month": "统计月份，YYYY-MM",
            "region": "销售区域",
            "product_code": "虚构产品编号",
            "product_name": "虚构产品名称",
            "sales_amount_cents": "销售额，整数分",
        },
        "supported_queries": [
            "按月份、区域、产品筛选销售额",
            "按 month、region、product 中的一个或多个维度汇总",
            "比较指定月份与上月销售额及环比变化",
        ],
        "unsupported": ["任意 SQL", "明细订单查询", "写入、修改或删除数据"],
    }


def query_sales_summary_data(
    *,
    month: str | None = None,
    region: str | None = None,
    product: str | None = None,
    group_by: list[str] | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """按允许维度汇总销售额；动态 SQL 片段只取自白名单。"""

    _validate_month(month)
    _validate_filters(region, product)
    groups = _validate_group_by(group_by or [])
    if not 1 <= limit <= MAX_RESULT_ROWS:
        raise RequestValidationError(
            f"limit 必须在 1 到 {MAX_RESULT_ROWS} 之间。"
        )

    group_columns = [GROUP_FIELDS[item] for item in groups]
    select_prefix = ", ".join(group_columns)
    if select_prefix:
        select_prefix += ", "
    where_sql, parameters = _where_clause(month, region, product)
    group_sql = f" GROUP BY {', '.join(group_columns)}" if group_columns else ""
    order_sql = f" ORDER BY {', '.join(group_columns)}" if group_columns else ""
    sql = (
        f"SELECT {select_prefix}COUNT(*) AS source_row_count, "
        "SUM(sales_amount_cents) AS total_cents "
        f"FROM sales_records{where_sql}{group_sql}{order_sql} LIMIT ?"
    )

    with readonly_connection() as connection:
        rows = connection.execute(sql, [*parameters, limit]).fetchall()

    # 无分组聚合在无记录时仍返回一行，因此必须用 COUNT(*) 明确区分。
    if not rows or (not groups and rows[0]["source_row_count"] == 0):
        return {
            "status": "no_data",
            "message": "当前筛选条件下没有销售记录。",
            "filters": {"month": month, "region": region, "product": product},
            "data_classification": "虚构模拟数据",
        }

    result_rows: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {
            "source_row_count": row["source_row_count"],
            **_money(row["total_cents"]),
        }
        if "month" in groups:
            item["month"] = row["month"]
        if "region" in groups:
            item["region"] = row["region"]
        if "product" in groups:
            item.update(_product_payload(row["product_code"]))
        result_rows.append(item)

    return {
        "status": "ok",
        "filters": {"month": month, "region": region, "product": product},
        "group_by": groups,
        "result_count": len(result_rows),
        "results": result_rows,
        "data_classification": "虚构模拟数据",
    }


def _previous_month(month: str) -> str:
    value = datetime.strptime(month, "%Y-%m")
    year = value.year if value.month > 1 else value.year - 1
    previous = value.month - 1 if value.month > 1 else 12
    return f"{year:04d}-{previous:02d}"


def _period_total(
    connection: sqlite3.Connection,
    *,
    month: str,
    region: str | None,
    product: str | None,
) -> tuple[int, int]:
    where_sql, parameters = _where_clause(month, region, product)
    row = connection.execute(
        "SELECT COUNT(*) AS record_count, "
        "COALESCE(SUM(sales_amount_cents), 0) AS total_cents "
        f"FROM sales_records{where_sql}",
        parameters,
    ).fetchone()
    return row["record_count"], row["total_cents"]


def compare_monthly_sales_data(
    *, month: str, region: str | None = None, product: str | None = None
) -> dict[str, Any]:
    """由代码计算当月、上月和环比；模型不负责金额运算。"""

    _validate_month(month)
    _validate_filters(region, product)
    previous_month = _previous_month(month)

    with readonly_connection() as connection:
        current_count, current_cents = _period_total(
            connection, month=month, region=region, product=product
        )
        previous_count, previous_cents = _period_total(
            connection, month=previous_month, region=region, product=product
        )

    filters = {"region": region, "product": product}
    if current_count == 0:
        return {
            "status": "no_data",
            "message": f"{month} 在当前筛选条件下没有销售记录。",
            "month": month,
            "previous_month": previous_month,
            "filters": filters,
            "data_classification": "虚构模拟数据",
        }

    absolute_change = current_cents - previous_cents
    if previous_count == 0:
        comparison_status = "previous_period_no_data"
        change_rate_percent = None
        message = "上月没有记录，无法计算环比百分比。"
    elif previous_cents == 0:
        comparison_status = "previous_period_zero"
        change_rate_percent = None
        message = "上月销售额为零，无法计算有意义的环比百分比。"
    else:
        comparison_status = "comparable"
        rate = (
            (Decimal(absolute_change) / Decimal(previous_cents)) * Decimal(100)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        change_rate_percent = f"{rate:.2f}"
        message = "环比已计算。"

    return {
        "status": "ok",
        "comparison_status": comparison_status,
        "message": message,
        "month": month,
        "previous_month": previous_month,
        "filters": filters,
        "current": {"record_count": current_count, **_money(current_cents)},
        "previous": {"record_count": previous_count, **_money(previous_cents)},
        "change": {
            **_money(absolute_change),
            "change_rate_percent": change_rate_percent,
        },
        "data_classification": "虚构模拟数据",
    }


def safe_call(function: Any, **kwargs: Any) -> dict[str, Any]:
    """把参数错误、无数据结果与运行错误转换为可区分的工具返回。"""

    try:
        return function(**kwargs)
    except RequestValidationError as error:
        return {
            "status": "invalid_request",
            "message": str(error),
            "data_classification": "虚构模拟数据",
        }
    except Exception as error:  # 仅向调用方返回安全摘要，不暴露路径或 SQL。
        return {
            "status": "internal_error",
            "message": "查询执行失败，请检查服务端日志或联系演示管理员。",
            "error_type": type(error).__name__,
            "data_classification": "虚构模拟数据",
        }
