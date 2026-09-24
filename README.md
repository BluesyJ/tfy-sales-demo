# TrueFoundry Sales Demo

用同一组虚构销售数据演示三种接入方式：原生 HTTP MCP、已有 REST API 转 MCP、Hosted STDIO。适合展示企业接口如何接入 TrueFoundry，再由 Agent 查询业务数据。

**销售同事先看 [演示流程](docs/demo-guide.md)，技术同事从 [启动与平台配置](docs/setup.md) 开始。**

## 三种方式

| 方式 | 代码入口 | 演示重点 |
|---|---|---|
| REST API → MCP | `api_server.py`、`openapi-sales-summary.json` | 复用已有 API，通过 OpenAPI 导入工具 |
| 原生 HTTP MCP | `server.py` | 接入已开发的远程 MCP 服务 |
| Hosted STDIO | [hosted_stdio/](hosted_stdio/) | 托管命令行 MCP，无需笔记本持续提供 HTTP 服务 |

三种方式任选一种即可完成基本演示，无需同时启动。旧的 [tfy-sales-demo-stdio](https://github.com/BluesyJ/tfy-sales-demo-stdio) 仓库继续保留，已有安装地址不变。

## 查询内容

- `get_sales_data_description`：说明字段、可用月份、区域和金额口径。
- `query_sales_summary`：按月份、区域、产品查询和汇总销售额。
- `compare_monthly_sales`：由服务端计算当月、上月金额与环比。

数据共18条，覆盖2026年7—8月、华东/华南/华北及三个虚构产品。金额以人民币分存储；工具只读，不接受任意 SQL。

| 示例问题 | 参考结果 |
|---|---|
| 2026年8月华东销售额是多少？ | 310,000.00元 |
| 2026年7月华东销售额是多少？ | 250,000.00元 |
| 8月华东销售额环比增长多少？ | 24.00% |

## 本地准备

需要 Python 3.11+。以下为 Windows PowerShell 命令：

```powershell
git clone https://github.com/BluesyJ/tfy-sales-demo.git
cd tfy-sales-demo
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-api.txt
.\.venv\Scripts\python.exe init_db.py
.\.venv\Scripts\python.exe local_checks.py
```

然后按 [启动说明](docs/setup.md) 设置独立的演示凭证，选择 API 或 MCP 服务。仅运行 Hosted STDIO 时，无需初始化根目录数据库；其数据随包提供。

## 平台演示范围

代码提供业务工具。Virtual MCP、成员权限、Policies、Guardrails 和 Request Traces 需要在自己的 TrueFoundry 工作区配置；本仓库不包含平台账号、模型 Key 或客户资料。

本 Demo 未实现 MCP 限流、自动熔断或 Agent 死循环检测。调用审批、内容拦截与异常流量熔断应分别验证，不能用其中一项代替另一项。

完整本地检查见 [验证记录](docs/validation.md)。平台联调结果需按工作区实际配置确认。

其他项目入口见 [项目导航](PROJECTS.md)。
