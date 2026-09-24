"""对正在运行的8020端口做本地HTTP与认证检查，不调用外部服务。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from api_server import app


BASE_URL = os.environ.get("SALES_API_BASE_URL", "http://127.0.0.1:8020")
AUTH_ENV_VAR = "SALES_API_BEARER_TOKEN"


def request_json(
    path: str, token: str | None = None
) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE_URL + path, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def main() -> None:
    token = os.environ.get(AUTH_ENV_VAR)
    if not token:
        raise RuntimeError(f"请先设置环境变量{AUTH_ENV_VAR}。")

    base_query = urllib.parse.urlencode({"month": "2026-08", "region": "华东"})
    code, _ = request_json(f"/sales/summary?{base_query}")
    assert code == 401

    code, _ = request_json(
        f"/sales/summary?{base_query}",
        "invalid-api-token-not-a-real-credential",
    )
    assert code == 401

    query = urllib.parse.urlencode({"month": "2026-08", "region": "华东"})
    code, body = request_json(f"/sales/summary?{query}", token)
    assert code == 200
    assert body["status"] == "ok"
    assert body["results"][0]["sales_amount_cents"] == 31_000_000
    assert body["results"][0]["sales_amount_yuan"] == "310000.00"

    query = urllib.parse.urlencode({"month": "2025-01", "region": "华东"})
    code, body = request_json(f"/sales/summary?{query}", token)
    assert code == 200
    assert body["status"] == "no_data"

    query = urllib.parse.urlencode({"month": "2026-08", "region": "华中"})
    code, body = request_json(f"/sales/summary?{query}", token)
    assert code == 422
    assert body["detail"]

    code, body = request_json("/sales/description", token)
    assert code == 200
    assert body["status"] == "ok"
    assert body["available_months"] == ["2026-07", "2026-08"]
    assert body["available_regions"] == ["华东", "华南", "华北"]

    query = urllib.parse.urlencode({"month": "2026-08", "region": "华东"})
    code, body = request_json(f"/sales/comparison?{query}", token)
    assert code == 200
    assert body["status"] == "ok"
    assert body["current"]["sales_amount_cents"] == 31_000_000
    assert body["previous"]["sales_amount_cents"] == 25_000_000
    assert body["change"]["change_rate_percent"] == "24.00"

    schema = app.openapi()
    expected_operations = {
        "/sales/description": "get_sales_data_description",
        "/sales/summary": "query_sales_summary",
        "/sales/comparison": "compare_monthly_sales",
    }
    assert set(schema["paths"]) == set(expected_operations)
    for path, operation_id in expected_operations.items():
        operation = schema["paths"][path]["get"]
        assert operation["operationId"] == operation_id
        assert operation["security"] == [{"SalesApiBearerAuth": []}]
    assert schema["components"]["securitySchemes"]["SalesApiBearerAuth"] == {
        "type": "http",
        "description": "独立的销售API测试Bearer Token。OpenAPI只声明认证方式，不包含Token值。",
        "scheme": "bearer",
    }

    code, _ = request_json("/openapi.json")
    assert code == 404

    print(
        "OpenAPI销售API本地检查通过：认证、数据说明、销售汇总、月度环比、"
        "无数据、非法参数、三个Operation Schema及文档未公开。"
    )


if __name__ == "__main__":
    main()
