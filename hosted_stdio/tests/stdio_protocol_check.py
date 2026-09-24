"""使用真实 MCP STDIO 客户端验证安装后的 console script。"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _payload(result: Any) -> dict[str, Any]:
    """优先读取结构化结果，兼容文本 JSON 返回。"""

    structured = getattr(result, "structured_content", None)
    if structured is None:
        structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured
    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)
        if text:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
    raise AssertionError("工具未返回可识别的结构化结果。")


async def check(command: str, args: list[str]) -> None:
    server = StdioServerParameters(command=command, args=args)
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            assert initialized.server_info.name == "Sales Data Query Demo"

            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            assert names == {
                "get_sales_data_description",
                "query_sales_summary",
                "compare_monthly_sales",
            }

            description = _payload(
                await session.call_tool("get_sales_data_description", {})
            )
            assert description["status"] == "ok"
            assert description["available_months"] == ["2026-07", "2026-08"]

            august = _payload(
                await session.call_tool(
                    "query_sales_summary",
                    {"month": "2026-08", "region": "华东"},
                )
            )
            assert august["results"][0]["sales_amount_cents"] == 31_000_000

            july = _payload(
                await session.call_tool(
                    "query_sales_summary",
                    {"month": "2026-07", "region": "华东"},
                )
            )
            assert july["results"][0]["sales_amount_cents"] == 25_000_000

            comparison = _payload(
                await session.call_tool(
                    "compare_monthly_sales",
                    {"month": "2026-08", "region": "华东"},
                )
            )
            assert comparison["comparison_status"] == "comparable"
            assert comparison["change"]["change_rate_percent"] == "24.00"

            no_data = _payload(
                await session.call_tool(
                    "query_sales_summary",
                    {"month": "2025-01", "region": "华东"},
                )
            )
            assert no_data["status"] == "no_data"

            invalid = _payload(
                await session.call_tool(
                    "query_sales_summary",
                    {"month": "2026-08", "region": "华中"},
                )
            )
            assert invalid["status"] == "invalid_request"

    print("STDIO协议检查通过：initialize、3个工具发现及6次工具调用。")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "用法：python tests/stdio_protocol_check.py <命令> [命令参数 ...]"
        )
    command = str(Path(sys.argv[1]).resolve())
    asyncio.run(check(command, sys.argv[2:]))


if __name__ == "__main__":
    main()
