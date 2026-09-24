"""通过 Streamable HTTP 验证销售问数 MCP 的工具发现与典型调用。"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from fastmcp import Client


SERVER_URL = os.environ.get(
    "SALES_MCP_SERVER_URL", "http://127.0.0.1:8010/mcp"
)
AUTH_ENV_VAR = "SALES_MCP_BEARER_TOKEN"


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if hasattr(value, "__dict__"):
        return {
            key: _jsonable(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return value


def show(title: str, value: Any) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(_jsonable(value), ensure_ascii=False, indent=2, default=str))


async def main() -> None:
    token = os.environ.get(AUTH_ENV_VAR)
    if not token:
        raise RuntimeError(f"请先设置环境变量 {AUTH_ENV_VAR}。")
    async with Client(SERVER_URL, auth=token) as client:
        show("工具列表", await client.list_tools())
        show("数据说明", await client.call_tool("get_sales_data_description", {}))
        show(
            "2026-08 华东销售额",
            await client.call_tool(
                "query_sales_summary", {"month": "2026-08", "region": "华东"}
            ),
        )
        show(
            "2026-08 华东各产品销售额",
            await client.call_tool(
                "query_sales_summary",
                {"month": "2026-08", "region": "华东", "group_by": ["product"]},
            ),
        )
        show(
            "2026-08 华东环比",
            await client.call_tool(
                "compare_monthly_sales", {"month": "2026-08", "region": "华东"}
            ),
        )
        show(
            "无数据月份",
            await client.call_tool(
                "query_sales_summary", {"month": "2025-01", "region": "华东"}
            ),
        )
        show(
            "非法区域",
            await client.call_tool(
                "query_sales_summary", {"month": "2026-08", "region": "华中"}
            ),
        )
        show(
            "非法分组字段",
            await client.call_tool(
                "query_sales_summary", {"month": "2026-08", "group_by": ["customer"]}
            ),
        )


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
