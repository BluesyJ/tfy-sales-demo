"""验证无Token、错误Token和正确Token三种认证路径，不输出凭证。"""

from __future__ import annotations

import asyncio
import os

from fastmcp import Client


SERVER_URL = os.environ.get(
    "SALES_MCP_SERVER_URL", "http://127.0.0.1:8010/mcp"
)
AUTH_ENV_VAR = "SALES_MCP_BEARER_TOKEN"


async def expect_rejected(label: str, auth: str | None) -> None:
    try:
        async with Client(SERVER_URL, auth=auth) as client:
            await client.list_tools()
    except Exception:
        print(f"通过：{label}被服务端拒绝。")
        return
    raise AssertionError(f"认证失败：{label}不应被允许访问。")


async def main() -> None:
    token = os.environ.get(AUTH_ENV_VAR)
    if not token:
        raise RuntimeError(f"请先设置环境变量 {AUTH_ENV_VAR}。")

    await expect_rejected("无Token请求", None)
    await expect_rejected("错误Token请求", "invalid-demo-token-not-a-real-credential")

    async with Client(SERVER_URL, auth=token) as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools} == {
            "get_sales_data_description",
            "query_sales_summary",
            "compare_monthly_sales",
        }
        result = await client.call_tool(
            "query_sales_summary", {"month": "2026-08", "region": "华东"}
        )
        assert result.data["status"] == "ok"
        assert result.data["results"][0]["sales_amount_cents"] == 31_000_000

    print("通过：正确Token可发现3个工具并查询2026年8月华东销售额。")
    print("认证验证完成；未输出任何Token。")


if __name__ == "__main__":
    asyncio.run(main())
