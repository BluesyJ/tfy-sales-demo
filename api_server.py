"""销售问数REST API，用于TrueFoundry OpenAPI转MCP对照实验。

它与原生MCP Server完全独立：复用sales_db.py的只读查询逻辑，但监听8020端口，
提供与原生MCP三个只读工具对应的HTTP接口。认证Token只从环境变量读取，
不写入OpenAPI或日志。
"""

from __future__ import annotations

import os
import secrets
from typing import Annotated, Literal

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from sales_db import (
    compare_monthly_sales_data,
    get_data_description,
    query_sales_summary_data,
    safe_call,
)


AUTH_ENV_VAR = "SALES_API_BEARER_TOKEN"
api_token = os.environ.get(AUTH_ENV_VAR, "")
if not api_token or len(api_token) < 32:
    raise RuntimeError(
        f"缺少独立API测试凭证：请通过环境变量{AUTH_ENV_VAR}提供至少32个字符的Token。"
    )

bearer_scheme = HTTPBearer(
    scheme_name="SalesApiBearerAuth",
    description="独立的销售API测试Bearer Token。OpenAPI只声明认证方式，不包含Token值。",
    auto_error=False,
)


def verify_bearer_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> None:
    """在业务查询执行前强制校验Token，不依赖调用方或模型自觉。"""

    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not secrets.compare_digest(credentials.credentials, api_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "unauthorized",
                "message": "缺少或使用了无效的Bearer Token。",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SalesSummaryRow(StrictModel):
    source_row_count: int = Field(description="参与本行汇总的模拟数据记录数。")
    sales_amount_cents: int = Field(description="销售额，整数分。")
    sales_amount_yuan: str = Field(
        description="销售额，人民币元字符串，固定保留两位小数。"
    )
    currency: Literal["CNY"] = Field(description="币种代码。")
    month: str | None = Field(default=None, description="按月份分组时返回，YYYY-MM。")
    region: str | None = Field(default=None, description="按区域分组时返回。")
    product_code: str | None = Field(default=None, description="按产品分组时返回。")
    product_name: str | None = Field(default=None, description="按产品分组时返回。")


class SalesFilters(StrictModel):
    month: str | None = None
    region: str | None = None
    product: str | None = None


class SalesSummarySuccess(StrictModel):
    status: Literal["ok"]
    filters: SalesFilters
    group_by: list[Literal["month", "region", "product"]]
    result_count: int
    results: list[SalesSummaryRow]
    data_classification: Literal["虚构模拟数据"]


class SalesSummaryNoData(StrictModel):
    status: Literal["no_data"]
    message: str
    filters: SalesFilters
    data_classification: Literal["虚构模拟数据"]


class ProductOption(StrictModel):
    product_code: str
    product_name: str


class SalesDataDescription(StrictModel):
    status: Literal["ok"]
    data_classification: Literal["虚构模拟数据"]
    dataset: str
    grain: str
    amount_definition: str
    available_months: list[str]
    available_regions: list[str]
    available_products: list[ProductOption]
    fields: dict[str, str]
    supported_queries: list[str]
    unsupported: list[str]


class ComparisonFilters(StrictModel):
    region: str | None = None
    product: str | None = None


class PeriodAmount(StrictModel):
    record_count: int
    sales_amount_cents: int
    sales_amount_yuan: str
    currency: Literal["CNY"]


class ChangeAmount(StrictModel):
    sales_amount_cents: int
    sales_amount_yuan: str
    currency: Literal["CNY"]
    change_rate_percent: str | None


class MonthlyComparisonSuccess(StrictModel):
    status: Literal["ok"]
    comparison_status: Literal[
        "comparable", "previous_period_no_data", "previous_period_zero"
    ]
    message: str
    month: str
    previous_month: str
    filters: ComparisonFilters
    current: PeriodAmount
    previous: PeriodAmount
    change: ChangeAmount
    data_classification: Literal["虚构模拟数据"]


class MonthlyComparisonNoData(StrictModel):
    status: Literal["no_data"]
    message: str
    month: str
    previous_month: str
    filters: ComparisonFilters
    data_classification: Literal["虚构模拟数据"]


class ApiError(StrictModel):
    code: str
    message: str


class ErrorEnvelope(StrictModel):
    detail: ApiError


app = FastAPI(
    title="模拟销售数据查询API",
    version="0.2.0",
    summary="用于OpenAPI转MCP对照实验的三个只读销售API",
    description=(
        "基于虚构销售数据、限定范围的业务问数API。"
        "复用现有只读SQLite查询逻辑，不接受任意SQL，不提供写入或删除能力。"
    ),
    # 规范仍由app.openapi()自动生成并导出，但运行服务不公开规范或交互文档。
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)


@app.get(
    "/sales/description",
    operation_id="get_sales_data_description",
    summary="读取模拟销售数据说明",
    description=(
        "返回数据范围、字段含义、金额单位、可用月份、区域、产品及支持的查询范围。"
        "该接口不需要业务参数。"
    ),
    response_model=SalesDataDescription,
    response_description="模拟销售数据的数据字典和查询边界。",
    responses={
        401: {"model": ErrorEnvelope, "description": "未提供或提供了无效凭证。"},
        500: {"model": ErrorEnvelope, "description": "服务端读取失败。"},
    },
    tags=["模拟销售查询"],
)
def get_sales_data_description_api(
    _: Annotated[None, Depends(verify_bearer_token)] = None,
) -> SalesDataDescription:
    result = safe_call(get_data_description)
    if result["status"] == "internal_error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": result["message"]},
        )
    return SalesDataDescription.model_validate(result)


@app.get(
    "/sales/summary",
    operation_id="query_sales_summary",
    summary="查询模拟销售额汇总",
    description=(
        "按月份和区域查询模拟销售额，可选按产品筛选或按白名单维度分组。"
        "金额在结果中同时以整数分和两位小数的人民币元字符串返回。"
    ),
    response_model=SalesSummarySuccess | SalesSummaryNoData,
    response_description="销售汇总结果，或明确的无数据结果。",
    responses={
        401: {"model": ErrorEnvelope, "description": "未提供或提供了无效凭证。"},
        422: {"description": "参数格式或取值不符合接口约束。"},
        500: {"model": ErrorEnvelope, "description": "服务端查询执行失败。"},
    },
    tags=["模拟销售查询"],
)
def query_sales_summary_api(
    month: Annotated[
        str,
        Query(
            description="统计月份，格式YYYY-MM，例如2026-08。",
            pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        ),
    ],
    region: Annotated[
        Literal["华东", "华南", "华北"],
        Query(description="销售区域：华东、华南或华北。"),
    ],
    product: Annotated[
        Literal["P-100", "P-200", "P-300"] | None,
        Query(description="可选虚构产品编号。"),
    ] = None,
    group_by: Annotated[
        list[Literal["month", "region", "product"]] | None,
        Query(
            description=(
                "可选分组维度，可重复传入group_by；只允许month、region、product。"
            )
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            description="最大返回行数；当前模拟数据最多使用50。",
            ge=1,
            le=50,
        ),
    ] = 50,
    _: Annotated[None, Depends(verify_bearer_token)] = None,
) -> SalesSummarySuccess | SalesSummaryNoData:
    result = safe_call(
        query_sales_summary_data,
        month=month,
        region=region,
        product=product,
        group_by=group_by,
        limit=limit,
    )

    if result["status"] == "invalid_request":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "invalid_request", "message": result["message"]},
        )
    if result["status"] == "internal_error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": result["message"]},
        )
    if result["status"] == "no_data":
        return SalesSummaryNoData.model_validate(result)
    return SalesSummarySuccess.model_validate(result)


@app.get(
    "/sales/comparison",
    operation_id="compare_monthly_sales",
    summary="比较当月与上月模拟销售额",
    description=(
        "按指定月份及可选区域、产品筛选，返回当月、上月、绝对变化和可计算时的"
        "环比百分比。计算由服务端完成，并区分上月无记录和上月销售额为零。"
    ),
    response_model=MonthlyComparisonSuccess | MonthlyComparisonNoData,
    response_description="月度销售比较结果，或明确的当月无数据结果。",
    responses={
        401: {"model": ErrorEnvelope, "description": "未提供或提供了无效凭证。"},
        422: {"description": "参数格式或取值不符合接口约束。"},
        500: {"model": ErrorEnvelope, "description": "服务端查询执行失败。"},
    },
    tags=["模拟销售查询"],
)
def compare_monthly_sales_api(
    month: Annotated[
        str,
        Query(
            description="待比较月份，格式YYYY-MM，例如2026-08。",
            pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        ),
    ],
    region: Annotated[
        Literal["华东", "华南", "华北"] | None,
        Query(description="可选销售区域。"),
    ] = None,
    product: Annotated[
        Literal["P-100", "P-200", "P-300"] | None,
        Query(description="可选虚构产品编号。"),
    ] = None,
    _: Annotated[None, Depends(verify_bearer_token)] = None,
) -> MonthlyComparisonSuccess | MonthlyComparisonNoData:
    result = safe_call(
        compare_monthly_sales_data,
        month=month,
        region=region,
        product=product,
    )

    if result["status"] == "invalid_request":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "invalid_request", "message": result["message"]},
        )
    if result["status"] == "internal_error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": result["message"]},
        )
    if result["status"] == "no_data":
        return MonthlyComparisonNoData.model_validate(result)
    return MonthlyComparisonSuccess.model_validate(result)


if __name__ == "__main__":
    # 独立端口；不影响原生MCP Server的8010端口。
    uvicorn.run(app, host="127.0.0.1", port=8020, log_level="info")
