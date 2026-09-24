"""初始化销售问数 Demo 的 SQLite 模拟数据库。

本文件只负责建表和写入固定的虚构数据；MCP 查询服务不会调用这里的写入逻辑。
重复运行会重置本 Demo 自己的 sales_records 表，便于恢复一致的演示基线。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "sales_demo.db"


# 金额统一按“人民币分”存储，避免浮点金额计算误差。
SALES_ROWS = [
    ("2026-07", "华东", "P-100", "星云分析终端", 12_000_000),
    ("2026-07", "华东", "P-200", "远航协作套件", 8_000_000),
    ("2026-07", "华东", "P-300", "清岚服务平台", 5_000_000),
    ("2026-07", "华南", "P-100", "星云分析终端", 9_000_000),
    ("2026-07", "华南", "P-200", "远航协作套件", 7_000_000),
    ("2026-07", "华南", "P-300", "清岚服务平台", 4_000_000),
    ("2026-07", "华北", "P-100", "星云分析终端", 6_000_000),
    ("2026-07", "华北", "P-200", "远航协作套件", 5_500_000),
    # 保留一条金额为零的记录，用于区分“有记录但金额为零”和“无记录”。
    ("2026-07", "华北", "P-300", "清岚服务平台", 0),
    ("2026-08", "华东", "P-100", "星云分析终端", 15_000_000),
    ("2026-08", "华东", "P-200", "远航协作套件", 9_500_000),
    ("2026-08", "华东", "P-300", "清岚服务平台", 6_500_000),
    ("2026-08", "华南", "P-100", "星云分析终端", 11_000_000),
    ("2026-08", "华南", "P-200", "远航协作套件", 8_500_000),
    ("2026-08", "华南", "P-300", "清岚服务平台", 4_500_000),
    ("2026-08", "华北", "P-100", "星云分析终端", 7_000_000),
    ("2026-08", "华北", "P-200", "远航协作套件", 6_000_000),
    ("2026-08", "华北", "P-300", "清岚服务平台", 3_000_000),
]


def initialize_database() -> Path:
    """建立并重置本 Demo 的唯一数据表，返回数据库路径。"""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sales_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                region TEXT NOT NULL,
                product_code TEXT NOT NULL,
                product_name TEXT NOT NULL,
                sales_amount_cents INTEGER NOT NULL CHECK (sales_amount_cents >= 0),
                UNIQUE (month, region, product_code)
            )
            """
        )
        connection.execute("DELETE FROM sales_records")
        connection.executemany(
            """
            INSERT INTO sales_records (
                month, region, product_code, product_name, sales_amount_cents
            ) VALUES (?, ?, ?, ?, ?)
            """,
            SALES_ROWS,
        )
        connection.commit()
    return DB_PATH


if __name__ == "__main__":
    path = initialize_database()
    print(f"已初始化模拟销售数据库：{path}")
    print(f"记录数：{len(SALES_ROWS)}；数据性质：虚构模拟数据")
