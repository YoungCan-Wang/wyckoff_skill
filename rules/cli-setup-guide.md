# 安装与配置指南

命令参考见 `rules/agent-interface.md`，这里只讲首次上手与排障。

## 引导顺序

每一步都依赖上一步，不要跳步。MCP 一步是可选的，执行前先问用户。

1. 安装 CLI
2. 注册并登录
3. 配置数据源（至少一个）
4. 配置模型
5. （可选）注册 MCP Server
6. 就绪：`wyckoff` 进 TUI、`wyckoff run "..."` 跑无界面任务，或在宿主里直接调 MCP 工具

## 1. 安装

任选一种：

```bash
# 一键安装（建 ~/.wyckoff/venv，自动装 uv）
curl -fsSL https://raw.githubusercontent.com/YoungCan-Wang/WyckoffTradingAgent/main/install.sh | bash

# Homebrew
brew tap YoungCan-Wang/wyckoff && brew install wyckoff

# 已有 Python 3.11+ 环境
uv pip install youngcan-wyckoff-analysis
```

验证：`wyckoff --version`。升级：`wyckoff update`。

不想用命令行的用户可以装桌面端：GitHub Releases 里 `desktop-v*` 标签下有 macOS（Intel / Apple Silicon）安装包。

## 2. 注册与登录

1. 打开 https://wyckoff-analysis.pages.dev/ 注册。
2. 让用户自己在终端执行（宿主是 Claude Code 时用 `!` 前缀）：
   ```bash
   wyckoff auth <email>
   ```
   密码交互输入。不要把密码写进命令参数，也不要让用户把密码发到对话里。
3. 验证：`wyckoff auth status`，看到 `✓ 已登录` 即可。显示「登录已过期」时重新执行第 2 步。

凭据保存在 `~/.wyckoff/`，token 过期会自动续登。宿主模型不得读取或复述这个目录下的任何内容。

## 3. 数据源

至少配一个，两个都配覆盖更好。值省略时会交互输入：

```bash
wyckoff config tushare      # 免费：https://tushare.pro/ 注册后复制 token
wyckoff config tickflow     # 付费，实时 + 历史，A / 港 / 美：https://tickflow.org/auth/register?ref=5N4NKTCPL4
wyckoff config              # 查看脱敏后的当前配置
```

## 4. 模型

```bash
wyckoff model add                                              # 交互
wyckoff model set <id> <provider> <api_key> --model <name>     # 非交互
wyckoff model list
```

供应商：`gemini`、`openai`、`claude`、`deepseek`。DeepSeek 可加 `--thinking-level off|low|high|max`。
自建代理用 `--base-url`。只有 `wyckoff run`、`report`、TUI 以及 MCP 的 `generate_ai_report` / `generate_strategy_decision`
会消耗这里配置的模型额度；其余 MCP 工具不调 LLM。

## 5. MCP Server（可选）

先问用户要不要接。要的话：

```bash
# Claude Code（不依赖本机已装的 CLI）
claude mcp add wyckoff -- uvx --from 'youngcan-wyckoff-analysis[mcp]' wyckoff-mcp

# 已经用 install.sh 装过 CLI 的，也可以直接用本机命令
claude mcp add wyckoff -- wyckoff-mcp
```

其他客户端（命令和参数分开填）：

```json
{
  "mcpServers": {
    "wyckoff": {
      "command": "uvx",
      "args": ["--from", "youngcan-wyckoff-analysis[mcp]", "wyckoff-mcp"]
    }
  }
}
```

- 不需要在 env 里放 token：完成第 2、3 步后，MCP server 第一次被业务调用时会读本机 CLI 登录态和配置。
- 持仓写入默认拒绝。用户明确要无人值守写入时，才在 `env` 里加 `"WYCKOFF_MCP_ALLOW_WRITES": "1"`；这代表用户接受风险，不是审批。
- 这是单用户的本地 stdio 进程，不能暴露成多人共享的 HTTP 服务。
- 注册后要重启宿主会话，工具才会出现。

## 排障

| 现象 | 原因与处理 |
|---|---|
| `bad interpreter: ~/.wyckoff/venv/bin/python: no such file or directory` | venv 指向的 uv 托管 Python 被清理了。重跑 install.sh 重建 venv |
| `wyckoff: error: unrecognized arguments` / `invalid choice` | 命令写法过期，跑 `wyckoff <子命令> --help`，对照 agent-interface 第三节 |
| `✗ 未知配置项: show` | 没有 `config show`，用 `wyckoff config` |
| 登录报「邮箱或密码错误」，但确认密码没错 | 多半写成了 `auth login <email>`，`login` 被当成邮箱。改用 `wyckoff auth <email>` |
| `portfolio cash 50000` 后余额没变 | 金额要写成 `--amount 50000` |
| MCP 返回 `WRITE_DENIED` | 预期行为，见上方第 5 步 |
| MCP 返回 `MISSING_DEPENDENCY` | 装的不是 `[mcp]` extra，或业务依赖缺失；用 uvx 那条命令重新注册 |
| 行情或模型调用失败 | MCP `diagnose_backend()`，或检查 `wyckoff config` / `wyckoff model list` |
| `wyckoff run` 说「已提交 N 项待批准」 | 写操作在审批队列里，`wyckoff approve list` 查看，`ok <id>` 批准；12 小时后过期 |
