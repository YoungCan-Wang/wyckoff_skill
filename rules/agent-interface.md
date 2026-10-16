# Agent 接口参考（MCP + CLI）

对齐来源：`integrations/public_mcp/contracts.py`（MCP 契约）、`cli/__main__.py::_build_parser`（CLI）、
`docs/PUBLIC_MCP.md`。命令行为有疑问时以 `wyckoff <子命令> --help` 的输出为准。

## 一、MCP 工具（19 个，契约版本 1.0）

在 Claude Code 里注册为 `wyckoff` 后，工具名形如 `mcp__wyckoff__analyze_stock`。
所有工具都拒绝未知参数；结果放在 `structuredContent`，顶层是数组时包成 `{"result": ...}`。

### 只读 / 研究

| 工具 | 参数（默认值） | 说明 |
|---|---|---|
| `search_stock_by_name` | `keyword` | 名称 / 代码 / 拼音首字母搜 A 股，结果在 `result` |
| `analyze_stock` | `code`, `mode="diagnose"`（diagnose / price / fundamental）, `cost=0`, `days=30` | 单只 A 股。diagnose=威科夫结构 + 健康度；price=OHLCV；fundamental=基本面研究，不改变正式买卖信号。传 `cost` 会带上成本视角 |
| `wyckoff_diagnose` | `code` | 纯引擎：交易区间、阶段、Spring/SOS/LPS/EVR 触发，不调 LLM |
| `market_regime` | — | 市场状态 `regime` 与动态阈值，不调 LLM。闸门判定见 decision-contract |
| `get_market_overview` | `trade_date=""`, `include_breadth=false` | 指数截面原始行情，**不含**市场状态判定 |
| `intraday_analysis` | `code` | 分钟级 VWAP、趋势、动量、量能 |
| `intraday_rescue_check` | `code` | 60 分钟结构、平台突破、VWAP 收复；不等于下单许可 |
| `query_history` | `source`（recommendation / signal / attribution）, `status="all"`, `limit=20` | 形态复盘 / 信号池 / 策略归因。历史记录不是当前可执行买单 |
| `screen_stocks` | `board="all"`, `limit=null`, `financial_metrics=null` | 选股漏斗。`limit` 留空=聊天快扫，`0`=全量；最长 600 秒 |
| `run_funnel_simulation` | `board="all"`, `limit=null` | 跑生产漏斗返回结构数据，不推送通知 |
| `run_backtest` | `start`, `end`, `hold_days=10`, `top_n=3`, `board="all"`, `stop_loss_pct=-7`, `take_profit_pct=18`, `entry_price_mode="open"`（open / close / tail_1455） | 回测生产漏斗，3–10 分钟 |
| `portfolio` | `mode="view"`（view / diagnose） | 读取或诊断当前本地用户持仓，需要登录态。云端读取失败时会静默回退本地 DB，留意 `valuation_updated_at` 是否陈旧 |
| `reassess_profile` | `report_text`, `profile="balanced"`（conservative / balanced / aggressive） | 按风格重评已有研报，只预览不落库 |
| `diagnose_backend` | — | 检查数据源与模型后端连通性 |

`board` 可选：`all`、`main_chinext`、`main`、`chinext`、`star`、`bse`。

### 消耗模型额度

| 工具 | 参数 | 说明 |
|---|---|---|
| `generate_ai_report` | `stock_codes`（1–100 个） | AI 研报，可能保存研究产物 |
| `generate_strategy_decision` | — | 基于当前持仓的攻防决策研究，不执行交易 |

### 写操作（默认拒绝）

| 工具 | 参数 | 说明 |
|---|---|---|
| `update_portfolio` | `action`（add / remove / update / set_cash / delete_records）, `code`, `name`, `buy_dt`, `shares`, `cost_price`, `free_cash`, `codes`, `items`, `table` | `add` 必须带 `buy_dt`；`set_cash` 必须显式给 `free_cash`（省略不等于 0）；多只一次用 `items` 打包 |
| `record_trade_fill` | `code`, `side`（buy / sell）, `shares`, `price`, `trade_date=""`, `name=""` | 回填已经发生的真实成交，增量更新持仓与现金。**不得自动重试** |
| `research_hypothesis` | `action`（create / list / detail / update / link_evidence / evaluate / transition）等 | 研究假设台账；仅 list / detail 不受写入闸门限制 |

### 写入闸门

MCP 没有审批环节，写操作在加载业务模块之前就会返回 `WRITE_DENIED`。处理顺序：
1. 首选让用户走 CLI（有审批）：`wyckoff portfolio ...` 或 `wyckoff run "..."` + `wyckoff approve ok <id>`。
2. 用户明确接受风险时，才建议在 MCP server 的 env 里设置 `WYCKOFF_MCP_ALLOW_WRITES=1` 并重启。不得替用户擅自打开。

### 持仓写入规则（MCP 与 CLI 通用）

- code 和 name 必须齐全：缺一个先用 `search_stock_by_name` 补；多个匹配让用户确认。
- `add` 必须有建仓日期（YYYYMMDD 或 YYYY-MM-DD）；用户没说就问，**不要默认填今天**。
- `update` 只改股数或成本时不传 `buy_dt`；目标不存在会报错，不得改成 add。
- 一次给多只时只调一次 `update_portfolio`，用 `items` 打包；写完最多再 `portfolio(mode="view")` 核对一次。
- 写完只确认结果，不自动追加诊断。

### 错误码

`UNKNOWN_TOOL`、`INVALID_ARGUMENTS`、`INPUT_TOO_LARGE`（输入 > 64 KiB）、`WRITE_DENIED`、`MISSING_DEPENDENCY`、
`TOOL_FAILED`、`INVALID_RESULT`、`RESULT_TOO_LARGE`（结果 > 1 MiB）。`isError=true` 时原样告诉用户错误码和含义，
不要把它当成分析结果。客户端超时不代表只读任务已经停止，不要立刻重发同一个长任务。

## 二、CLI 命令参考

### 账户 / 模型 / 配置

| 命令 | 说明 |
|---|---|
| `wyckoff auth <email>` | 登录；密码省略时交互输入。**没有 `login` 子命令**，`auth login <email>` 会把 `login` 当邮箱 |
| `wyckoff auth status` / `wyckoff auth logout` | 状态 / 登出 |
| `wyckoff model list` | 已配置模型 |
| `wyckoff model add` | 交互添加 |
| `wyckoff model set <id> <provider> <api_key> [--model X] [--base-url X] [--thinking-level off/low/high/max]` | 非交互添加；`--thinking-level` 仅 deepseek |
| `wyckoff model rm <id>` / `default <id>` / `fallback` / `usage [--days 7]` / `cost` / `refresh` | 删除 / 设默认 / 降级链 / 用量 / 成本 / 刷新目录 |
| `wyckoff config` | 打印脱敏配置（**没有 `show` 子命令**） |
| `wyckoff config tushare\|tickflow [value]` | 设置数据源；省略 value 时交互输入 |
| `wyckoff config stream_timeout\|tool_timeout <秒>` | 超时设置 |

### 持仓（`portfolio` / `pf`）

| 命令 | 说明 |
|---|---|
| `wyckoff portfolio list` | 持仓、可用资金、总权益、止损 |
| `wyckoff portfolio add <code> --name X --shares N --cost X --buy-dt YYYYMMDD` | 新增；`--buy-dt` 必填。**股数和成本不能写成位置参数** |
| `wyckoff portfolio rm <code>` | 删除 |
| `wyckoff portfolio cash` | 查看可用资金 |
| `wyckoff portfolio cash --amount 50000` | 设置可用资金。**`portfolio cash 50000` 不会报错，只会显示余额，金额被静默丢弃** |
| `wyckoff portfolio fill <code> --side buy\|sell --shares N --price X [--date YYYYMMDD]` | 回填真实成交 |

### 信号 / 复盘

| 命令 | 说明 |
|---|---|
| `wyckoff signal [all\|pending\|survived\|confirmed\|expired] [-n 30]` | 信号确认池；无 `--json` 参数，要结构化数据用 MCP `query_history` |
| `wyckoff recommend [-n 20]`（`rec`） | 威科夫形态复盘记录，**不是买入推荐** |

### 分析与任务

| 命令 | 说明 |
|---|---|
| `wyckoff screen [--board all/main/chinext/gem/star/bse] [--limit N] [--style trend/pullback/quality] [--financial-metrics \| --no-financial-metrics]` | 全市场漏斗；`--limit 0` 为全量 |
| `wyckoff backtest [--hold-days 10] [--months 18] [--top-n 4]`（`bt`） | 回测整个漏斗策略，**不接受股票代码** |
| `wyckoff report <code1,code2>` | AI 深度研报，消耗模型额度 |
| `wyckoff run "<指令>"` | 无界面跑一轮 agent；写操作进入审批队列并打印编号 |
| `wyckoff approve list` / `ok <id>` / `no <id>` | 处理待批准写操作；12 小时过期 |
| `wyckoff dashboard [--port 8765]`（`dash`） | 本地可视化面板 |
| `wyckoff daemon [--status] [--foreground]` | 常驻定时调度 |
| `wyckoff workflow [list\|show\|events\|resume] [run_id]`（`wf`） | 动态 workflow |

### 会话 / 诊断 / 维护

| 命令 | 说明 |
|---|---|
| `wyckoff` | 交互 TUI |
| `wyckoff session [list\|export\|fork]`、`wyckoff log`、`wyckoff trace`、`wyckoff diag` | 会话、日志、运行轨迹、诊断包 |
| `wyckoff memory [list\|search\|clear\|delete\|trace]`（`mem`） | agent 记忆 |
| `wyckoff prompt [list\|show\|render] <name>` | 查看 / 渲染 prompt 模板 |
| `wyckoff sync [status]` / `wyckoff cleanup [--days 30]` | Supabase → 本地 SQLite 同步 / 清理 |
| `wyckoff mcp` | 启动本项目 MCP server（等同 `wyckoff-mcp`） |
| `wyckoff mcp-add <name> --command X [--args ...] [--env KEY]` / `mcp-list` / `mcp-test` / `mcp-enable` / `mcp-disable` / `mcp-remove` | 给 agent 接**外部** MCP server；新增后默认未启用 |
| `wyckoff update` / `wyckoff --version` | 升级 / 版本 |

## 三、旧 skill 写法对照（已失效）

| 旧写法 | 现在 |
|---|---|
| `wyckoff auth login <email> <password>` | `wyckoff auth <email>`（密码交互输入） |
| `wyckoff config show` | `wyckoff config` |
| `portfolio add <code> <shares> <cost>` | `portfolio add <code> --name X --shares N --cost X --buy-dt YYYYMMDD` |
| `portfolio cash <amount>` | `portfolio cash --amount <amount>` |
| `signal --json` / `recommend --json` | MCP `query_history` |
| `backtest <code>` | `backtest --hold-days/--months/--top-n`（整个漏斗） |
| MCP `diagnose_stock` | `analyze_stock(mode="diagnose")` |
| MCP `get_stock_price` | `analyze_stock(mode="price")` |
| MCP `get_portfolio` / `diagnose_portfolio` | `portfolio(mode="view" / "diagnose")` |
| MCP `get_signal_pending` / `get_recommendation_tracking` | `query_history(source="signal" / "recommendation")` |
| MCP `get_tail_buy_history` | 已移除 |
