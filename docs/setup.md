# 启动与平台配置

本文命令在仓库根目录执行。Windows 使用 `.\.venv\Scripts\python.exe`；Linux/macOS 替换为 `.venv/bin/python`。依赖安装见首页。

## 1. 已有 API 转 MCP

设置仅用于本次演示的 Bearer Token，至少32个字符。以下命令隐藏输入，不把凭证写进脚本或终端历史：

```powershell
$secureToken = Read-Host '输入 API 演示 Token（至少32字符）' -AsSecureString
$env:SALES_API_BEARER_TOKEN = [System.Net.NetworkCredential]::new('', $secureToken).Password
.\.venv\Scripts\python.exe init_db.py
.\.venv\Scripts\python.exe api_server.py
```

保持终端运行，服务监听 `http://127.0.0.1:8020`。三个接口均需 `Authorization: Bearer <API演示Token>`：

| 方法 | 路径 | Operation ID |
|---|---|---|
| GET | `/sales/description` | `get_sales_data_description` |
| GET | `/sales/summary?month=2026-08&region=华东` | `query_sales_summary` |
| GET | `/sales/comparison?month=2026-08&region=华东` | `compare_monthly_sales` |

`/sales/summary` 要求 month 和 region；还可传 product、group_by、limit。参数以导出的 OpenAPI 为准。

平台操作：

1. 在 MCP Servers 中新增 OpenAPI 服务，选择 **Paste Spec**，粘贴根目录 `openapi-sales-summary.json`。
2. 配置网关可访问的 HTTPS 后端地址。SaaS 无法直接访问笔记本的 `127.0.0.1`；可使用自行部署的 HTTPS 服务或临时演示隧道。临时隧道变化后更新后端地址。
3. 当前 Spec 不内嵌部署地址。如果界面要求从 OpenAPI 的 `servers` 字段读取地址，可在 JSON 顶层添加 `"servers": [{"url": "https://你的演示域名"}]`，使用实际后端地址并保持三个接口路径不变。
4. 在后端认证配置中填写 API Bearer Token；若使用 Additional Headers，则填写 `Authorization: Bearer <API演示Token>`。不要把真实 Token 放入 OpenAPI 文本。
5. 保存后检查三个工具及参数，在 Playground 调用销售查询。

该服务有意关闭 `/openapi.json`、`/docs` 和 `/redoc`，因此默认使用 **Paste Spec**。**Build via URL** 需要可获取的 OpenAPI 文档 URL，不能仅填写业务 API 地址。

修改接口后，在已设置 API Token 的另一个终端重新导出：

```powershell
.\.venv\Scripts\python.exe export_openapi.py
```

## 2. 原生 HTTP MCP

```powershell
$secureToken = Read-Host '输入 MCP 演示 Token（至少32字符）' -AsSecureString
$env:SALES_MCP_BEARER_TOKEN = [System.Net.NetworkCredential]::new('', $secureToken).Password
.\.venv\Scripts\python.exe init_db.py
.\.venv\Scripts\python.exe server.py
```

服务监听 `http://127.0.0.1:8010/mcp`，使用 Streamable HTTP。平台新增远程 MCP，填写网关可访问的 HTTPS 地址并保留 `/mcp` 路径，配置对应 MCP Bearer Token。

在另一个设置了相同 Token 的终端检查：

```powershell
.\.venv\Scripts\python.exe auth_checks.py
.\.venv\Scripts\python.exe client_demo.py
```

可通过 `SALES_MCP_SERVER_URL` 指定另一个测试入口。认证使用 FastMCP 的开发测试验证器；生产接入应对接正式身份系统。

## 3. Hosted STDIO

完整说明与平台 JSON 见 [hosted_stdio/README.md](../hosted_stdio/README.md)。本地安装：

```powershell
.\.venv\Scripts\python.exe -m pip install ./hosted_stdio
.\.venv\Scripts\tfy-sales-demo.exe
```

命令启动后等待 MCP 协议输入，没有网页界面。由 MCP 客户端或平台启动和调用它。

## 两层凭证不要混淆

| 链路 | 使用的凭证 |
|---|---|
| 客户端 → TrueFoundry 网关 | 用户或 Virtual Account 的 TFY Token |
| TrueFoundry → REST API / HTTP MCP | 本文配置的独立后端 Bearer Token |
| Hosted STDIO → 本 Demo 数据 | 不需要下游凭证，使用包内虚构数据 |

根目录服务默认绑定本机回环地址；本仓库不自动打开公网隧道。演示结束后停止服务，并清除当前终端变量：

```powershell
Remove-Item Env:SALES_API_BEARER_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:SALES_MCP_BEARER_TOKEN -ErrorAction SilentlyContinue
```
