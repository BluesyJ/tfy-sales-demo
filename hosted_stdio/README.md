# Sales Demo — Hosted STDIO

三个只读销售工具，查询随包提供的18条虚构记录。使用内存 SQLite，不依赖 HTTP 服务、公网隧道或外部数据库。

## 本地安装

在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe -m pip install ./hosted_stdio
.\.venv\Scripts\tfy-sales-demo.exe
```

客户端配置使用安装后的 `tfy-sales-demo` 可执行文件完整路径。它通过标准输入输出通信；手动启动后等待输入是正常现象。

## TrueFoundry 托管配置

在新增 Hosted STDIO MCP 的配置中粘贴以下 JSON。这里沿用原独立仓库的固定版本，以保持已有安装方式：

```json
{
  "mcpServers": {
    "tfy-sales-demo": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/BluesyJ/tfy-sales-demo-stdio.git@v0.1.0",
        "tfy-sales-demo"
      ]
    }
  }
}
```

本包无需 Env Auth。平台仍需能获取依赖，并完成工具发现、调用与权限验证。包的本地协议验证不等于目标 SaaS 工作区已验证。

本目录保留原包名、命令入口和 MIT 许可证；完整场景说明见 [主 README](../README.md)。
