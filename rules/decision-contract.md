# 决策契约（与 agent 风控对齐）

对齐来源：`core/market_trade_mode.py`、`core/prompts.py`（`_DECISION_EVIDENCE_CONTRACT`、
`PRIVATE_PM_DECISION_JSON_PROMPT`、`CHAT_AGENT_SYSTEM_PROMPT`）、`llmdoc/portfolio_exit_discipline.md`、
`GLOSSARY.md`。本文件只约束宿主模型怎么下结论，不改变 agent 的任何参数。

## 1. 市场闸门（先于一切买入类动作）

用 `market_regime()` 拿 `regime`（通道 C 下让 agent 报告「大盘水温」）。返回 `error`、取不到值或值不认识时，按
`UNKNOWN` 处理。

| regime | 新开仓权限 | 允许的买入类动作 |
|---|---|---|
| `UNKNOWN` / `RISK_OFF` / `CRASH` / `BLACK_SWAN` | 硬防守：禁止新开 | 无 |
| `RISK_ON` | 过热：禁止新仓（过热追新历史负期望） | 无，只做研究对照 |
| `BEAR_REBOUND` / `PANIC_REPAIR` | 修复观察：禁止新仓 | 无，只验证修复强度 |
| `NEUTRAL` | **生产环境在下单闸门禁买名单内**：禁止正式推荐与新开。NEUTRAL 震荡期正式推荐绝对收益为负；已有持仓严守既有止损、不加仓 | 无 |
| `CAUTION` | 谨慎试探 | 最多一只、二次确认后的 `PROBE`；禁止 `ATTACK` |
| `PANIC_REPAIR_CONFIRMED` / `PANIC_REPAIR_INTRADAY` | 修复成立 | 只开放一只小额 `PROBE`；禁止 `ATTACK`、追价和自动扩仓 |

说明：
- `NEUTRAL` 的禁买来自生产工作流的 `STEP4_BUY_BLOCK_REGIMES=UNKNOWN,NEUTRAL,PANIC_REPAIR,RISK_OFF,CRASH,BLACK_SWAN`。
  本地 `market_regime` 不读这个配置，所以本地看到 `NEUTRAL` 不代表放行，按生产口径处理。
- 在当前生产配置下，没有任何 regime 会进入「可执行买入（mainline_active）」档；最宽松的也只是单只 `PROBE`。
  如果用户说「现在能不能满仓干」，直接引用这一条。
- 闸门只管**新增风险敞口**。持仓的 `HOLD` / `TRIM` / `EXIT` 不受闸门限制，按第 3 节判断。
- 对已有持仓加仓（`is_add_on=true`）与新开仓同等对待：闸门禁止新开时也禁止加仓。

## 2. 候选状态链：研究 ≠ 买单

| 状态 | 含义 | 能否下单 |
|---|---|---|
| `DETECTED`（库内 `pending`） | 当日结构命中 | 否 |
| `SURVIVED` | 跨日未失效 | 否 |
| `VALIDATED`（库内 `confirmed`） | 需求已确认 | 仅当市场闸门允许时可称为「可执行候选」（次日开盘价附近） |
| `OMS_APPROVED` | OMS 最终核准 | 实际下单仍需用户确认 |

- `screen_stocks` 的结果、「处于起跳板」、「主线核心」、形态复盘记录、单股诊断的 `priority_watch` / `trigger_watch`
  都是研究语义。单股诊断的 `direct_buy_allowed` 恒为 false。
- `candidate_theme`、`candidate_phase`、`candidate_role`、`candidate_lane`、`health`、`track` 这些程序字段只能原样引用，
  不得改判或编造。
- 主线标签只提高比较优先级，不能覆盖硬止损、确认破位、过热风险、数据质量门槛和市场闸门。

## 3. 动作词表与证据门槛

动作只用 agent 的枚举（中文括注给用户看）：

| 动作 | 含义 | 必须同时给出 |
|---|---|---|
| `HOLD`（持有） | 不动 | 观察条件 / 生死线 |
| `TRIM`（减仓） | 小幅减仓 | `signal_severity` ∈ {`HARD_RISK`, `CONFIRMED_BREAK`}，`action_timing`，减仓比例区间，可否证的价格或事件证据 |
| `EXIT`（清仓） | 全部卖出 | 同 TRIM |
| `PROBE`（试探买入） | 小额试单意图 | 闸门允许；`entry_zone` 区间 + `stop_loss` + 盘面确认条件 + 取消条件 |
| `ATTACK`（进攻买入） | 加大买入意图 | 闸门允许 ATTACK（当前生产配置下没有任何档位允许）；字段同 PROBE |

`signal_severity`：`NONE` / `WARNING` / `CONFIRMED_BREAK` / `HARD_RISK`
- `WARNING` 只是预警，**不允许**生成可执行的 TRIM / EXIT；普通技术走弱必须等收盘或次日确认。
- 只有 `HARD_RISK`（有效止损已触发、重大实锤风险）或 `CONFIRMED_BREAK`（收盘确认破位 / 派发）允许 TRIM / EXIT。
  证明不了就改成 `HOLD`，并写清楚「什么情况会升级」。

`action_timing`：`NOW` / `CLOSE_CONFIRM` / `NEXT_SESSION_IF` / `ON_REBOUND` / `WAIT`
- `WAIT`、`CLOSE_CONFIRM` 表示还没形成可执行指令。
- 盘中价格接近当日低点、收盘还没确认时，除 `HARD_RISK` 外不得立即卖出，应给 `CLOSE_CONFIRM` / `ON_REBOUND` / `WAIT`。
- 非交易时段不得给 `NOW`。
- 买入类动作要区分「趋势强」和「价格过度延伸」：高开或脱离支撑时等回踩或收盘确认，不追。

`confidence`（可选）是证据支持度，不是上涨概率。

## 4. 证据与账户边界

- 行情、基本面、估值、新闻、市场广度各有独立的可用性和时点；缺失、过期或没提供的，不得自行补全，必须标「缺失」。
- 默认 `capital_scope=account_only`：现金、持仓权重、总权益只代表这个证券账户，不代表用户全部资产。用户没有明确说
  「这是我全部可投资资产」时，**不得**仅凭单股权重、现金比例或行业集中度给出 TRIM / EXIT。
- 先评价股票本身（质量、趋势、供需、事件风险），再谈它在账户里的角色。成本和浮盈亏只是执行与风险背景，不是股票好坏的证据。
- 不计算仓位比例、金额和股数（agent 侧由 OMS 决定）。空仓有现金时，给「分批触发条件 + 取消条件」，不给金额。
- 证据不足时直接写「证据不足，保持不动」。
- 新闻只用于解释事件日的异常量价，不得作为买卖依据，不得推翻结构判断。

## 5. 持仓退出纪律

- 先分硬退出与酌情退出：止损已触发、确认破位、明确派发、账户级风控否决属于硬退出，可直接 `EXIT`，不得拿案例或叙事拖延止损。
- 题材降温、持有时间偏长、基本面吸引力下降但结构未坏，属于酌情退出：比较 `HOLD` / `TRIM` / `EXIT` 的机会成本。
- 高辨识度、反复受事件驱动且流动性充足的持仓，在没有硬退出证据时，可以 `TRIM` 后留小额尾仓；尾仓也要有明确失效条件，不能变成无限期死扛。
- 单日涨停不能反证此前所有风险判断。已清仓后出现涨停，不得为了弥补错过而追价；重新开仓仍须过候选准入和市场闸门。

## 6. 组合场景的决策顺序

1. 每只持仓独立判断，给 `HOLD` / `TRIM` / `EXIT`（或闸门允许时的加仓 `PROBE` + `is_add_on=true`）。
2. 有候选股时：先过闸门。闸门禁止新开 → 候选只列观察条件，结论固定为「继续持有原仓位 / 保留现金」。闸门允许 → 与结构最弱的持仓比较，
   只有在结构质量、供需失衡程度、起爆迫切性上**明显**更强时才给换入；仅仅「看起来不错」就保持不动。
3. 空仓有现金时：闸门禁止新开 → 保留现金，给观察清单和解禁条件（regime 变成什么、候选走到哪个状态）；闸门允许 → 最多按闸门允许的只数给 `PROBE` 计划。
4. 默认偏好是「少动、等确认、保现金」，不是「名单来了就交易」。
5. 写一句组合级 `market_view`，例如「防守优先，只保留一只试单猎物」。
