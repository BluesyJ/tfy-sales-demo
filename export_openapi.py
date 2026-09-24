"""从FastAPI运行时模型导出OpenAPI，避免手工维护重复定义。"""

from __future__ import annotations

import json
from pathlib import Path

from api_server import app


OUTPUT_PATH = Path(__file__).resolve().parent / "openapi-sales-summary.json"


if __name__ == "__main__":
    OUTPUT_PATH.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已从FastAPI自动生成：{OUTPUT_PATH}")
