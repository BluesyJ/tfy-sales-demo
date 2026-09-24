"""可由 TrueFoundry Hosted STDIO 启动的销售问数 MCP Server。"""

from __future__ import annotations

import logging
import sys
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from .sales_db import (
    compare_monthly_sales_data,
    get_data_description,
    query_sales_summary_data,
    safe_call,
)


mcp = FastMCP(
    name="Sales Data Query Demo",
    instructions=(
        "这是基于18条虚构销售数据、限定查询范围的业务问数 Demo。"
        "只允许读取和汇总，不支持任意 SQL、写入、修改或删除。"
    ),
)


@mcp.tool(
    description="返回模拟销售数据的范围、字段、金额口径及可用筛选值。",
    annotations={"readOnlyHint": True, "destructiveHint": False},
)
def get_sales_data_description() -> dict[str, Any]:
    return safe_call(get_data_description)


@mcp.tool(
    description=(
        "按可选月份、区域和产品编号筛选，并按允许维度汇总模拟销售额。"
        "group_by 只允许 month、region、product；不接受 SQL。"
    ),
    annotations={"readOnlyHint": True, "destructiveHint": False},
)
def query_sales_summary(
    month: Annotated[
        str | None, Field(description="可选统计月份，格式 YYYY-MM，例如 2026-08。")
    ] = None,
    region: Annotated[
        str | None, Field(description="可选区域：华东、华南或华北。")
    ] = None,
    product: Annotated[
        str | None,
        Field(description="可选产品编号：P-100、P-200 或 P-300。"),
    ] = None,
    group_by: Annotated[
        list[str] | None,
        Field(
            description="可选分组字段数组，只允许 month、region、product；不需要分组时省略。"
        ),
    ] = None,
    limit: Annotated[
        int, Field(description="最大返回行数，范围 1～50。", ge=1, le=50)
    ] = 50,
) -> dict[str, Any]:
    return safe_call(
        query_sales_summary_data,
        month=month,
        region=region,
        product=product,
        group_by=group_by,
        limit=limit,
    )


@mcp.tool(
    description=(
        "比较指定月份与上月的模拟销售额，返回绝对变化和可计算时的环比百分比。"
        "可按区域和产品编号筛选。"
    ),
    annotations={"readOnlyHint": True, "destructiveHint": False},
)
def compare_monthly_sales(
    month: Annotated[
        str, Field(description="待比较月份，格式 YYYY-MM，例如 2026-08。")
    ],
    region: Annotated[
        str | None, Field(description="可选区域：华东、华南或华北。")
    ] = None,
    product: Annotated[
        str | None,
        Field(description="可选产品编号：P-100、P-200 或 P-300。"),
    ] = None,
) -> dict[str, Any]:
    return safe_call(
        compare_monthly_sales_data,
        month=month,
        region=region,
        product=product,
    )


def main() -> None:
    """启动 STDIO 传输；禁止 banner，确保 stdout 只承载 MCP 协议。"""

    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
