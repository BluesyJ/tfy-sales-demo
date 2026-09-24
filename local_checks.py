"""不依赖外部模型的确定性检查，核对模拟数据库的关键参考结果。"""

from __future__ import annotations

import sqlite3

from init_db import initialize_database
from sales_db import (
    compare_monthly_sales_data,
    query_sales_summary_data,
    readonly_connection,
    safe_call,
)


def main() -> None:
    initialize_database()

    east_august = query_sales_summary_data(month="2026-08", region="华东")
    assert east_august["status"] == "ok"
    assert east_august["results"][0]["sales_amount_cents"] == 31_000_000

    by_product = query_sales_summary_data(
        month="2026-08", region="华东", group_by=["product"]
    )
    assert [row["sales_amount_cents"] for row in by_product["results"]] == [
        15_000_000,
        9_500_000,
        6_500_000,
    ]

    comparison = compare_monthly_sales_data(month="2026-08", region="华东")
    assert comparison["comparison_status"] == "comparable"
    assert comparison["current"]["sales_amount_cents"] == 31_000_000
    assert comparison["previous"]["sales_amount_cents"] == 25_000_000
    assert comparison["change"]["change_rate_percent"] == "24.00"

    no_data = query_sales_summary_data(month="2025-01", region="华东")
    assert no_data["status"] == "no_data"

    zero_record = query_sales_summary_data(
        month="2026-07", region="华北", product="P-300"
    )
    assert zero_record["status"] == "ok"
    assert zero_record["results"][0]["sales_amount_cents"] == 0

    invalid = safe_call(
        query_sales_summary_data, month="2026-08", region="华中"
    )
    assert invalid["status"] == "invalid_request"

    previous_missing = compare_monthly_sales_data(month="2026-07", region="华东")
    assert previous_missing["comparison_status"] == "previous_period_no_data"
    assert previous_missing["change"]["change_rate_percent"] is None

    previous_zero = compare_monthly_sales_data(
        month="2026-08", region="华北", product="P-300"
    )
    assert previous_zero["comparison_status"] == "previous_period_zero"
    assert previous_zero["change"]["change_rate_percent"] is None

    try:
        with readonly_connection() as connection:
            connection.execute(
                "INSERT INTO sales_records "
                "(month, region, product_code, product_name, sales_amount_cents) "
                "VALUES (?, ?, ?, ?, ?)",
                ("2026-09", "华东", "P-100", "星云分析终端", 1),
            )
    except sqlite3.OperationalError as error:
        assert "readonly" in str(error).lower()
    else:
        raise AssertionError("只读连接不应允许写入。")

    print("本地确定性检查通过：9 项。")


if __name__ == "__main__":
    main()
