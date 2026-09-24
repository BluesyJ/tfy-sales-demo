"""销售数据问数 MCP Server：只读、限定范围、全部使用模拟数据。"""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from pydantic import Field

from sales_db import (
    compare_monthly_sales_data,
    get_data_description,
    query_sales_summary_data,
    safe_call,
)


AUTH_ENV_VAR = "SALES_MCP_BEARER_TOKEN"
access_token = os.environ.get(AUTH_ENV_VAR, "")
if not access_token or len(access_token) < 32:
    raise RuntimeError(
        f"缺少独立测试凭证：请通过环境变量 {AUTH_ENV_VAR} 提供至少32个字符的Token。"
    )

# StaticTokenVerifier 是 FastMCP 官方提供的开发/测试验证器。
# Token仅从进程环境读取，不写入代码、数据库或日志；生产环境应改用正式身份系统。
auth = StaticTokenVerifier(
    tokens={
        access_token: {
            "client_id": "truefoundry-sales-mcp-demo",
            "scopes": ["sales:read"],
        }
    },
    required_scopes=["sales:read"],
)

mcp = FastMCP(
    name="Sales Data Query Demo",
    instructions=(
        "这是基于虚构销售数据、限定查询范围的业务问数 Demo。"
        "只允许读取和汇总，不支持任意 SQL、写入、修改或删除。"
    ),
    auth=auth,
)


@mcp.tool(
    description="返回模拟销售数据的范围、字段、金额口径及可用筛选值。",
    annotations={"readOnlyHint": True, "destructiveHint": False},
)
def get_sales_data_description() -> dict[str, Any]:
    """在查询前了解数据字典；不执行数据修改。"""

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
    """查询汇总；所有值用参数绑定，分组字段在查询层再次执行白名单校验。"""

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
    """环比由服务端代码计算，并区分上月无记录和上月销售额为零。"""

    return safe_call(
        compare_monthly_sales_data,
        month=month,
        region=region,
        product=product,
    )


if __name__ == "__main__":
    # 阶段 A 仅绑定本机回环地址，不创建公网入口。
    mcp.run(transport="http", host="127.0.0.1", port=8010, path="/mcp")
