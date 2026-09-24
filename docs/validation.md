# 本地验证记录

2026-09-24，在发布副本执行检查，未连接 TrueFoundry、外部模型或客户系统。

| 检查 | 结果 |
|---|---|
| 确定性数据、金额、边界条件与数据库只读 | `local_checks.py` 9项通过 |
| API 与 HTTP MCP 缺少/过短 Token | 均拒绝启动 |
| REST API 无 Token、错误 Token、正确 Token | 分别拒绝、拒绝、查询成功 |
| API 数据说明、金额、环比、无数据及非法参数 | 通过 |
| OpenAPI 三个 Operation、认证声明、禁用公开文档 | 通过 |
| HTTP MCP 工具发现与认证 | 拒绝无效身份，正确身份发现3个工具并查询成功 |
| 当前环境 STDIO 协议复跑 | Windows 执行沙箱拒绝子进程管道访问，未完成 |
| TrueFoundry 工作区完整联调 | 本次发布未执行 |

HTTP 检查使用临时生成的凭证与独立本地端口，不占用默认演示端口。

保留原项目检查脚本，供需要时自行使用。安装 STDIO 包后，其原有检查入口为：

```powershell
.\.venv\Scripts\python.exe hosted_stdio/tests/stdio_protocol_check.py .\.venv\Scripts\tfy-sales-demo.exe
```

工作区中的护栏、权限与审计需按 [演示流程](demo-guide.md) 单独验证。
