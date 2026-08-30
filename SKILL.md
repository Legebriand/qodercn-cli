---
name: qodercn-cli
name_en: Qoder CLI CN Delegation
name_zh: Qoder CN CLI 协同
description: Delegate coding and repository work to the standalone Qoder CLI CN runtime (qodercn / qoderclicn), which keeps its own login and credit pool. Supports headless -p calls, the official qodercn-agent-sdk with can_use_tool permission callbacks, and ACP stdio orchestration. Use when the user mentions qodercn, qoderclicn, QoderCN, a second opinion or cross-check review from another agent, or asks to build, implement, debug, fix, refactor or review code through it. Do NOT use for one-line edits, reading a single file, or work needing no external install.
description_en: Delegate coding and repository work to the standalone Qoder CLI CN runtime (qodercn / qoderclicn), which keeps its own login and credit pool. Supports headless -p calls, the official qodercn-agent-sdk with can_use_tool permission callbacks, and ACP stdio orchestration. Use when the user mentions qodercn, qoderclicn, QoderCN, a second opinion or cross-check review from another agent, or asks to build, implement, debug, fix, refactor or review code through it. Do NOT use for one-line edits, reading a single file, or work needing no external install.
description_zh: 把编码与仓库类工作委派给独立安装的 Qoder CLI CN（qodercn / qoderclicn），它有自己的登录态和独立额度池。支持 headless -p 调用、官方 qodercn-agent-sdk（含 can_use_tool 授权回调）以及 ACP stdio 编排。当用户提到 qodercn、qoderclicn、QoderCN，或要求由另一个 agent 给出第二意见、交叉复审，或要求用它来开发、实现、调试、修复、重构、审查代码时使用。不适用于一行小改、读单个文件，或无需外部安装的任务。
argument-hint: Describe the task and give the project path
argument-hint-en: Describe the task and give the project path
argument-hint-zh: 描述任务，并给出项目目录
user-invocable: true
version: 7.7.2
---

# Qoder CN CLI 协同（Qoder CLI CN）

Qoder CLI CN 与 QwenWork 共用同一套 agent 引擎，但是**独立安装的产品**：配置目录
`~/.qoder-cn`，独立登录态，**独立额度池**。这里的调用不计入 QwenWork 额度，
大任务前先告知用户这一点。

正文结论按证据来源分级，见文末「事实来源分层」：**只有 V 级是本机执行验证**，
D/C 级不得当作既成事实引用。

## 快速开始

默认走 headless 单发，始终通过清洗包装脚本调用，**不要直接执行
`qoderclicn.exe`**：

```bash
QN="$HOME/.qwenworkcn/skills/qodercn-cli/assets/qcn.sh"
"$QN" status && "$QN" --list-models          # 先验登录态与可用性
"$QN" -p "<任务描述>" -o json -w "C:\\路径\\到\\项目" \
     --permission-mode accept_edits --allowed-tools Write --max-turns 20

# accept_edits 只放行工作目录内的文件编辑；--allowed-tools 是单值，多工具需重复传参
# 秒退回 is_error=true/turns=1/credits=0 且 stderr 空 = 该模型池耗尽(118)
# 还能用哪个模型 → assets/usage_info.py（零 credits，读得到 SDK 漏掉的 Qwen 专属包）
# 目录不受信时非 default 模式会被静默降级 -> 无头下表现为"所有工具被拒"
```

需要中途授权、改写工具参数或实时进度时，走 Agent SDK 的 `assets/ask_relay.py`
（见「交互桥接」）；只有在无法安装 SDK 时才用 ACP 客户端。

## 第一步永远是清洗环境

`QODER_AGENT_SDK_ENTRYPOINT` **不是垃圾变量，而是 SDK 与 CLI 之间的握手标记**：
它表示"有宿主在驱动我，必须走 stream-json 协议"。QwenWork 本身就是 SDK 宿主，
会向每个 shell 导出 `sdk-ts` 和 `QODER_SDK_AUTH_PAYLOAD_FILE`，你的 shell 只是
**意外继承**了它们。

继承后果二选一，都很隐蔽：

```
sdk_invalid_args: ... Expected --print --input-format stream-json
--output-format stream-json, got print=true, inputFormat=undefined
```

该报错会让你补旗标 —— **不要照做**，补旗标等于被迫实现整套协议；正确做法是删变量。

### 删什么、留什么

按名字精确删除，**绝不能用前缀正则**（早期版本用 `^(QODER|QODERCN|DWS)`，会静默毁掉用户的 PAT 认证和默认
模型）。**名单的唯一权威是 `assets/qcn.sh` 里的 `is_pollution()`** 与三份 Python 清洗器的
`POLLUTION_EXACT` / `POLLUTION_FAMILIES` —— 不要把名单抄进本节，抄一次就多一个会过期的副本（这条本身
就是本轮之前踩过的重复源）。

必须保留的同族合法变量：`QODERCN_PERSONAL_ACCESS_TOKEN`（**PAT 覆盖已保存登录**）、`QODERCN_MODEL`、
`QODERCN_SUBAGENT_MODEL`、`QODERCN_PERMISSION_MODE`、`QODERCN_WORKING_DIR`、`QODERCN_SESSION_ID`、
`QODERCN_SESSION_NAME`、`QODERCN_APPEND_SYSTEM_PROMPT`、`QODERCN_MEMORY*`、`QODERCN_SANDBOX*`、
`QODER_MCP_LAZY`、`QODER_ASR_URL`、`QODER_CLI_MAX_CONCURRENT_SUBAGENTS`、`QODERCLI_PATH`（撞上
`QODERCLI_*` 前缀却是用户指定运行时的入口，三份清洗器都留了显式白名单），以及文档化特性开关
（如 `QODERCN_FEATURE_CROSS_SESSION`）—— **特性开关按精确名删，不按 `QODER_FEATURE_*` 家族删**。
`QODER_FEATURE_TASKS` 既被 QwenWork 注入又是文档变量，无法凭名字区分，按"隔离宿主优先"处理为删除。

`QODERCLI_*`（QwenWork 的运行时打包标记）与 `QODER_CLI_*`（CLI 自身的子代理并发上限）是两个家族，不能混。
改名单前先跟文档变量表对账，判定交给脚本本身（`source` 出 `is_pollution` 逐名问，见「验证清单」），不要在
注释里手抄。`qcn.sh` 另有四道自守卫：拒绝 `$HOME` 之外的 `QCN_HOME`、校验 `cygpath` 输出形如 `X:\`、
按 `=` 取完整变量名（覆盖含连字符的污染）、调用方自带 `--config-dir` 时不再强行覆盖。

## 认证

两条路径，**优先级只有一条规则**：

1. 浏览器 `/login`（别名 `/signin`）→ 落地 `~/.qoder-cn/.auth`，自动续期。
   用 `"$QN" status` 确认。
2. PAT → `QODERCN_PERSONAL_ACCESS_TOKEN`，在
   `https://qoder.cn/account/integrations` 生成，适合 CI 与无浏览器环境。

**PAT 覆盖已保存的登录。** 一个失效 token 会让健康安装直接拒绝启动：

```
QoderAuthError: ... contains a token that was rejected. It overrides any
saved login, so unset it or set a valid token
```

因此原先可用的环境突然报错时，**先查这个变量**，别怀疑安装。要回到浏览器登录
必须先清除它（`/logout` 同理）。

无浏览器环境（`CI`、`BROWSER=www-browser`、`DEBIAN_FRONTEND=noninteractive`、
`SSH_CONNECTION`、Linux 无 `DISPLAY`）会打印登录 URL 而不是尝试开浏览器。

## 通道选择（三条可用 + 一条已评估未采纳）

| 形态 | 我的往返次数 | 能否中途问人 | 适用 |
|---|---|---|---|
| `-p` headless | 1 | 不能，需确认的一律 auto-deny | 默认选择 |
| Agent SDK | 1 | 能，`can_use_tool` | 需要授权、改参数、中断 |
| ACP stdio | 脚本化 1；逐条转达则 N | 能，`session/request_permission` | 装不上 SDK 时 |

**三者都必须自己清洗环境**，SDK 也不会替你隔离。

**第四条通道：已评估、未采纳。** 官方 `cloud-agents` 版块（265 页）已给 Managed Mode 完整路径：网关
`https://api.qoder.com.cn/api/v1/cloud`，纯 curl + SSE，自带连通性探针（`GET /agents?limit=1`），认证走
`pt-` 前缀 PAT 换 SAT；吸引力在把长任务挪离本机。**但本机仍不可达**（2026-08-30 实测
`api.qoder.com.cn`/`openapi.qoder.com.cn` 503、`api.qoder.cn` 000，`--remote` 仍 `exit 42`）→ 只升出处，不升可用性。

### -p headless

```bash
"$QN" -p "<任务>" -w "C:\\项目路径"                      # 纯文本
echo "<任务>" | "$QN" -p                                # 从 stdin 喂
"$QN" -p "<任务>" --tools "" --no-session-persistence   # 只读意见，最便宜
"$QN" -p "<任务>" --max-turns 10 -w "C:\\项目路径"       # 兜住失控
```

`-o/--output-format` 只有 `text`、`json`、`stream-json` 三种。
headless 下没人能回答确认，所以要用 `--permission-mode` 预授权。六种模式
（`default`、`plan`、`auto`、`accept_edits`、`dont_ask`、`bypass_permissions`），
但 `--help` 只列五种、漏了 `plan`。`--yolo` 与
`--dangerously-skip-permissions` 都是 `bypass_permissions` 的别名，未经用户明确要求
不要使用。旗标值大小写不敏感（`acceptEdits`/`yolo` 实测可解析，非法值报六枚举 `Choices`）。

大批旗标虽不在 `--help` 中但确实存在（用"故意加一个假旗标、看解析器点名谁"的方式
验过）：`--acp`、`--sandbox`、`--max-turns`、`-q`、`--yolo`、`--fork-session`、
`-c`、`--settings`、`--output-style`、`--attachment`、`--reasoning-effort`、
`--context-window`、`--max-output-tokens`、`--strict-mcp-config`、
`--mcp-config`、`--disallowed-tools`、`--input-format`。

### JSON 信封

```bash
"$QN" -p "<任务>" -o json -w "C:\\项目路径" \
  | python -c "import sys,json;d=json.load(sys.stdin);print(d['result']); \
print('credits',d['total_credits'],'turns',d['num_turns'])"
```

字段：`type`、`subtype`、`is_error`、`num_turns`、`result`、`stop_reason`、`error_code`、
`errors`、`duration_ms`、`duration_api_ms`、`total_cost_usd`、`total_credits`（不是
`total_cost_credits`）、`usage`、`modelUsage`、`permission_denials`、`session_id`、`uuid`、
`fast_mode_state`。**`is_error` 的原因只写在 `error_code` + `errors[]` 里**，信封别处不提示。

两个读数陷阱：CN 的 `usage` token 计数恒为 0，唯一真实计量是 `total_credits`；
`modelUsage` 的键是**内部计费桶 ID 而非模型显示名**（`gfmodel` 即 GLM-5.3-Flash、
`qmodel_38max` 即 Qwen3.8-Max），不能拿桶名判断"模型没切换"。

信封里没有的运行时真相可以现查：每次无头运行都往 run 日志落一条
`[session.runtime_config] model=<桶> reasoning_effort=<档> context_window=<值>`，比 credits 干净得多
（实测 `--reasoning-effort xhigh` 确实抵达无头会话）。

另有一条实测边界：**`-p` 被 `--max-turns` 掐断时，信封 `is_error:true` 且根本
没有 `result` 键**，直接取 `d['result']` 会 KeyError；解析用 `d.get('result')`。该情形有官方锚
`subtype=error_max_turns` / 码 `47902` / 进程退出码 `53`（errors.md），不再只是单次本机观察。

## Agent SDK

```bash
pip install qodercn-agent-sdk        # Python 3.10+；TS 为 @qodercn-ai/qodercn-agent-sdk
python "$HOME/.qwenworkcn/skills/qodercn-cli/assets/sdk_bridge.py" \
  --cwd "C:\\项目路径" --prompt "<任务>" \
  --model Qwen3.8-Flash --permission-mode default --log gate.jsonl
```

四个文档没写、每个都花掉一轮排查的要点：

1. **`auth` 必填**，且不会隐式读 `~/.qoder-cn/.auth`，否则
   `AuthNotConfiguredError`。用 `qodercli_auth()`，其 payload 为
   `{"type":"qodercli"}`，含义是"复用现有 CLI 登录"（与 ACP 广播的
   `authMethods:[{id:"qoderclicn-login"}]` 对应）。另有 `access_token*()`、`service_account*()`
   （回调位真名 `fetch_service_account_token`；authentication.md 查无 `job_token` 待核）与 `on_auth_expired`。SDK 通过
   `mkdtemp(prefix="qoder-sdk-auth-")/payload.json`（0600）+
   `QODER_SDK_AUTH_PAYLOAD_FILE` 传递 —— 与 QwenWork 自身的做法逐字节同源，
   这也是区分"真宿主"与"意外继承"的依据。
2. **它把你的环境原样透传**。继承来的 `QODERCN_CONFIG_DIR` /
   `QODERCN_SERVER_ENDPOINT` 会让子进程去错误位置找凭据，表现为
   `Control request timeout: initialize` —— 看着像认证或版本问题，两者都不是。
   `QoderAgentOptions.env` 接受 `{变量名: None}`，语义是"从子进程删掉这个变量"；
   `sdk_bridge.py` 已把 shell 黑名单镜像过去。
3. **内置运行时版本偏旧**，且以 153.7MB 的 `_bundled/qoderclicn.exe` 形式存在。
   **务必用 `cli_path` 钉住自己的安装**。查找顺序：`options.cli_path` →
   `QODERCLI_PATH` → 内置 → PATH。`QODER_SKIP_VERSION_CHECK` 可跳过版本校验。
4. **SDK 选项标准是 camelCase**（`acceptEdits`、`bypassPermissions`、`dontAsk`，另有 `yolo`）；
   CLI 旗标大小写不敏感（`acceptEdits`/`yolo` 实测可解析），snake_case 亦可。`bypassPermissions`/
   `yolo` 在 SDK 还须同时传 `allow_dangerously_skip_permissions=True`（官方双重确认要求）。

回调契约：`CanUseTool(tool_name, input: dict, ctx) ->
Awaitable[PermissionResult]`；`PermissionResultAllow(behavior, updated_input,
updated_permissions, decision_classification)` 与
`PermissionResultDeny(behavior, message, interrupt)`。
**执行前改写参数已实测生效**：在 `updated_input` 里改掉 `file_path`，agent 就写到了
改名后的目标。`set_permission_mode` 是出向控制请求，可会话中途改档。

传 `settings` 对象时，**SDK 会自动合并 `general.fileCheckpointing.enabled = true`**
（已有该配置时以 SDK 选项为准），即走 SDK 且带 settings 就自带文件检查点；`-p` 路径不享有
这个默认，需自己确保可回退。

务必把协议噪音挡在上下文之外：一个极小任务就产出 5 条 `SystemMessage` +
8 条 `Assistant`/`User` + 1 条 `ResultMessage`。`sdk_bridge.py` 的做法是把每次被
网关放行的调用写进 `--log`，stdout 只吐一行摘要。

### 无头授权与回退

- **不传 `can_use_tool` 时，一切需确认的操作失败**，与 `permission_mode` 无关。失败发生在**工具层**：
  agent 看到 `Permission confirmation required but no interactive handler is available`，而信封照旧
  `is_error:false`、`permission_denials:[]`、credits 照扣。故 `is_error:false` + 一句"已完成"
  **不能**证明动过文件，必须查产物。
- **`acceptEdits` 的目录内编辑根本不经回调**：同一 Write 任务落盘成功而回调调用计数为 0。想靠
  `ask_relay.py` 拦编辑，必须用 `default`/`plan` 档，`acceptEdits` 会把它短路掉。
- **`--allowed-tools <tool>` 是单值**（详见下方「源码级已证」）：`'Read,Write'` 是一个
  token 而非两项，多工具需重复传参；且它是**限制不是授权**。
- **Rewind 无头可用**，配方见 `assets/rewind_files.py`：`query(text, message_uuid=<自定>)` →
  `rewind_files(uuid, dry_run=True)` 预览 → 去 `dry_run` 应用。锚点必须自供（SDK 自动生成的不回传）；
  `insertions/deletions` 只在预览里有意义（应用后归零）；`session_store` 与 `enable_file_checkpointing`
  互斥。`rollback` 与此无关 —— 它是 CLI **版本**回退。
- **跨进程 Rewind 成立**（`assets/xproc_rewind.py`，A/B 两个独立进程）：A 写入后退出，B 用
  `resume=<session_id>` 连上，预览 `canRewind:true` + 正确路径，应用后磁盘退回旧内容。检查点是**磁盘
  状态** `~/.qoder-cn/file-history/<session-id>/<hash>@vN`，故进程退出不丢；但**不能加
  `--no-session-persistence`**（会话不落盘就没有可续的锚点）。**快照只覆盖 `Write`/`Edit` 产物**：
  Bash 重定向落盘、目录级副作用、MCP/远程/数据库等外部效果**均不撤销**（`cli/sdk/checkpoint.md`）
  —— 委派惯用 shell 写文件，此时"改坏了能 rewind"静默失效，兜底仍要回到 git 提交。

## 交互桥接（人工授权转接）

`assets/ask_relay.py` 把 `can_use_tool` 挂到一对文件信箱上：脚本持有 SDK 会话并阻塞等待，
每个待决操作向 `--outbox` 追加一行 JSON（`{id, tool, input}`），宿主把它转成人话问题，
再把 `N: allow` / `N: allow_always` / `N: deny 理由` 追加进 `--inbox` 即继续。用文件而非
stdin 是因为宿主每次调用都是新进程、无法跨调用维持 stdin；后台进程还会继承 stdout/stderr
占住宿主管道，启动时必须全量重定向。

```bash
A="$HOME/.qwenworkcn/skills/qodercn-cli/assets"
T=$(mktemp -d); P=$(cygpath -w "$T")     # 必须用 cygpath；手写 "C:\x" 会得到非法目录
cd "$A" && nohup python ask_relay.py --cwd "$P" --prompt "<任务>"      --outbox "$T/q.jsonl" --inbox "$T/a.txt" --out "$T/sum.json"      --permission-mode default --on-timeout deny --ask-timeout 200      > "$T/relay.log" 2>&1 < /dev/null & disown

# 读 $T/q.jsonl 取待决操作 -> AskUserQuestion 问人 -> 把答复追加进 $T/a.txt
```

已实证：`Write`、`Read` 两次请求均正确浮出，答复 `1: allow` 后目标文件真实生成。
`--on-timeout deny` 保证没人答就绝不放行，可当默认档；`allow_always` 对应 ACP 的
`proceed_always`，此后同会话不再提问。

## 权限系统实测结论

用探针验的是**结果**，不是返回值 —— 因为 `permission_denials` **不记录规则命中**，
拿它验证规则等于什么都没测。

成立：
- `<project>/.qoder/settings.json` 确实加载（用 `model.name` 作示踪剂，桶变成
  `qmodel_38max` 且未传 `-m`）。
- `permissions.deny` 的**相对路径**形式有效：`Edit(editme.txt)` 拦住了改写
  （文件保持原内容），`Read(secret.txt)` 拦住了读取。Edit 那条在同时传
  `--allowed-tools Edit` 时依然拦得住。
- **`--add-dir` 授予工作目录外的写权限**（三臂 + 对照组）：`acceptEdits` 下 cwd 内控制组落盘（探针
  有效性得证）；目录外**不给** `--add-dir` → Write 与 Bash 双双被挡、文件不存在；给了 → 落盘成功。
  三臂的 `permission_denials` **全是 `[]`** —— 硬阻断也不记，别拿它验权限。

不成立 —— 这一组是安全边界，务必按"不可依赖"处理：
- **盘符绝对路径形式的规则静默不匹配**。`Read(C:/Users/.../secret.txt)` 直接泄露，
  而相对形式拦住。**不要用 `C:\` 或 `C:/` 前缀写 deny 规则**，用相对形式并按结果复核。
  （只测了正斜杠形式。）
- **`Bash(cmd:*)` 参数级规则确实有效**（推翻本技能早先的否定结论）。双臂实测：
  `permissions.allow: ["Bash(echo:*)"]` + `--permission-mode default` 下，命中规则的
  `echo` 落盘成功；不命中的 `git commit` 被拒，且 `git rev-list --count` 证明它确实没执行。
  早先的错误结论源于两个混淆变量：只读 shell 命令有独立自动放行通道，且 `default` 下
  Bash 一律被拒 —— 两者都让"过滤是否生效"不可观测。
- **`--allowed-tools` 单独不构成授权**：`default` 下即便写了它，工作目录内的 Write 仍被拒。
- **无头写文件的最小配方 = `--permission-mode accept_edits` + `--allowed-tools Write`，二者缺一不可**
  （同任务双臂实测：只给 `accept_edits` 无产物；补上 `--allowed-tools Write` 产物落地）。
- `--settings` 内联 JSON **压不过 `-m`**（同时给出时结算桶仍是 `gfmodel`）。文档称
  `--settings` 优先级最高，对模型选择不成立。
- 非法 `--settings` JSON 报的是 `Settings file not found: C:\{broken`；非法枚举值
  （如 `defaultPermissionMode: "zzz"`）被静默接受。

### CN 的规则词汇（D 级，未逐条执行）
规则写法、folderTrust 默认值、未受信目录不加载 Rules/Hooks/MCP/AGENTS.md 等原文细节已移到
[EVIDENCE.md](assets/EVIDENCE.md)「CN 规则词汇原文」。**已实测的两条留在上面「成立」清单里**：
CWD 即受信目录、`--add-dir` 能授予目录外写权限。

## 模型与计费

模型名**不要猜**，先 `"$QN" --list-models`（1.1.37 实测 13 款，含 DeepSeek-V4/GLM-5.3/Kimi-K2.7-Code；名称大小写
敏感，与文档 `cli_models.md` 冲突时以实时输出为准）。`-m` 语义：默认与新模型用**显示名**、Custom 用 modelID；问某名字背后是什么会得到策略性拒答。

计费桶 ID ↔ 显示名（逐名实测）：`qfmodel`=Qwen3.8-Flash、`q37fmodel`=Qwen3.7-Flash、`qmodel`=Qwen3.7-Plus、
`qmodel_38max`=Qwen3.8-Max；`gfmodel`=GLM-5.3-Flash 属**本机推断**（553 页文档站 0 命中 `gfmodel`/`GLM-5.3`，
文档表止于 GLM-5.2），1.1.37 那 13 款的新桶名需重新取证。**极小单回合 credits**：Flash 0.0468 / Qwen3.7-Flash 0.113 /
Max 0.563 / Plus 1.13 —— 24 倍差且**与档位顺序不一致**，别按"新版更贵"猜。**但成本随上下文走**：553 页审计这类大上下文
任务实测 Max 3.58、Flash 0.34 credits/回合。最便宜档 = Qwen3.8-Flash（已钉 `~/.qoder-cn/settings.json` 的 `model.name`）。

**`error_code=118`：以前记为"间歇故障"，其实是按模型分布的池耗尽。** 特征是 5-6 秒秒退、`is_error:true` +
`num_turns:1` + `total_credits:0` + `modelUsage` 只剩一个全零 `<synthetic>` 桶 + **stderr 为空**；真话只在
`errors[]` 里：`You've reached your credit usage limit`。`<synthetic>` = 请求根本没到达模型。所以"突然全挂"
先读 `errors[]` 再换模型，别怀疑安装/认证。两种失败要分开：**未识别** id 会在 stderr 提示
`not available right now; using "<X>" instead` 并回落账号默认（`~/.qoder-cn/.models/default` 的 `key`）；
**已识别但池空**的 id（含 `Auto`）什么都不提示，直接 118。

**两边都是每日发放的有限池，没有"随便花的那一侧"**，而且这事无头可查、零 credits：见下方「额度读数」。
`118` = bundle 常量 `personalCreditsDrainedOut:118`；官方码表（SDK errors 页）：116 团队管理员 / 117 团队成员 /
119 **所选模型**免费额度 / 122 Billing Group。归类名 `quota_exhausted` 等**见于本机转写，非文档字段**。

### 额度读数（零成本，别再去猜池子）

`assets/usage_info.py` 走 SDK 控制请求 `get_usage_info`（不打模型、不扣积分），拿到与交互 `/usage` 同源的数据：
`userQuota`（计划池）/ `addOnQuota` / `orgResourcePackage` / `totalUsagePercentage` / `isQuotaExceeded` /
`expiresAt`，外加会话 `session.total_credits`。**陷阱：SDK 归一化只映射那三个桶，把 `dedicatedResourcePackages`
整个丢掉**，而每日 Qwen 专属积分正住在里面 —— 它会报 `isQuotaExceeded=true / remaining=0` 而专属包里还剩几百。
脚本因此回读本次 run 日志里的原始 payload 补齐，末尾给一行 `VERDICT`。判"这模型还能不能用"用它，不用 `118` 表象。第三个读数入口是**桌面 GUI**（`C:/Program Files/Qoder/Qoder CN/Qoder CN.exe` 的用量页），与 CLI 同账号同后端、肉眼最快；
但它给的刷新时刻与 API 的 `expiresAt` **不一致**，两侧原文与判据见 EVIDENCE.md 台账。

我方成本（决定总开销的是这个）：长对话中**我一个回合约 0.39 QwenWork 积分**（上下文较短时约 0.19，随上下文
增长上升），而 Qoder CN CLI 跑完整件事才 0.16 —— 单个往返已约为其负载的 2.4 倍，交互式会成倍放大贵的那一侧。
做法：一次委派覆盖整个任务；大产出落盘、只回一行摘要 + 路径；`--max-turns` 就是预算（40 回合烧 44.8、
20 回合烧 34.5，都跑满才断且断在产物不完整处）；审计/批量校验按每项 1-2 回合估，宁拆多次小委派。

## 会话与项目作用域

会话按工作目录派生的 project key 存放（`~/.qoder-cn/projects/<mangled-path>`，底层是 SQLite，IDE 发行版
另带 `session-db-doctor`）。换 cwd 恢复会报 `Invalid session identifier ...`（原文见 EVIDENCE.md）。

```bash
"$QN" --list-sessions                        # 在 originates 的项目目录里执行
cd "C:/项目路径" && "$QN" -r "<session_id>" -p "继续"
"$QN" --fork-session -r "<id>" -p "<任务>"    # 分叉而非续写
```

`--continue`/`--resume`/`--remote`/`--remote-session`/`--teleport`/
`--remote-control` 互斥。打算续聊就不要加 `--no-session-persistence`。

## 记忆与子代理（路径已实测）

- `<project>/AGENTS.md` **会被加载**。
- `~/.qoder-cn/AGENTS.md` **会被加载**（2026-08-29 双臂探针实证：令牌只进文件、提示词不含，
  实验臂回吐令牌、无文件对照臂 NOTFOUND）——用户级与项目级两级入口均可靠，与官方 memory.md 一致。
- 子代理：用户级 `~/.qoder-cn/agents/<name>.md` **生效**（数量 5→6 并出现 `User:` 分组）；项目级是
  **`<project>/.qoder/agents/`**，而 `.agents/`、`.agents/agents/`、`.qoder-cn/agents/` 全部**未被识别**。
  CLI 子代理存放位置文档整体未记载（553 页 0 命中 `<project>/agents/`），此条纯本机实测；frontmatter 用 `name`/`description`/`tools`。
- 内置 5 个子代理：`Explore`、`general-purpose`、`Plan`、`qoder-guide`、
  `statusline-setup`；用 `qodercn agents list` 查看。

## 子命令

14 个命令全部实测存在（`plugin`/`skill`/`hook`/`agent` 是 `plugins`/`skills`/`hooks`/`agents` 的别名，连别名共 18 个
名字）：`mcp`、`plugins`、`plugin`、`skills`、`skill`、`hooks`、`hook`、`agents`、`agent`、`login`、`commit`、
`rollback`、`update`、`remote-control`、`status`、`security`、`feedback`、`config`。`--help` 只列 2 个，**缺席不代表没有**。

- **`hooks list` 是错的**（`error: too many arguments for 'hooks'. Expected 0
  arguments`）：实测 `hooks` 仅接受 `migrate`（从 Claude Code 迁移）。
- `config set` 只认 `vpc_endpoint`；模型等多数设置**不能**经它修改。
- `skills list` 看不到任何 QwenWork 技能，可用来确认存储隔离。
- **`rollback` 与"撤销改动"无关**（`--help` 实测）：它是 **CLI 自身版本回退**，
  `--to <version>`，默认回到 safe rollback version。别把它放进"改坏了怎么恢复"的路径。
- 回退机制叫 **Rewind**：交互入口 `/rewind`；**无头入口在 SDK 层** ——
  开检查点 `enable_file_checkpointing`(Py) / `enableFileCheckpointing`(TS)，再调
  `rewind_files(user_message_id)` / `rewindFiles(userMessageId, ...)`，锚点即信封与
  SDK 结果里的 `userMessageId`。文档明确：**手动编辑与 Shell 产生的改动可能不在还原
  范围内**，无 checkpoint 就没有可回退快照。无头委派仍以 **git 提交**为主兜底。

## 路径与 Shell 陷阱

- 文档口径命令是 `qodercn`（`~/.qoder-cn/entry` 里的 dispatcher）；真实二进制是
  `~/.qoder-cn/bin/qoderclicn/qoderclicn.exe`。都不是 `qodercli`（国际版，本机未装）。
- **本机没有任何 shell 能照文档跑通**：git-bash 不套 `PATHEXT`，`qodercn` 是 `.cmd`
  故 `command not found`；`cmd.exe //c` 和 `powershell.exe` 能解析，但仍带着被污染的
  环境启动子进程而失败。必须走包装脚本。
- 配置目录 `~/.qoder-cn`（**不是** `~/.qoder`）；但项目目录两边都叫 `.qoder/`。
- `-w` / `--add-dir` 要 Windows 路径，`/c/a/b` 会破坏 project keying；小心
  `cygpath -w` 吐出 8.3 短名（`LEGEBR~1`）。
- Windows 原生 `python` 读不了 `/tmp/...`（只有 MSYS 工具能），且默认编码 cp936：
  要传 Windows 路径并显式 `encoding='utf-8'`。
- Bash 的 cwd 跨调用保留；在解包出的源码目录里跑 `pip`，其 `types.py` 会遮蔽标准库
  导致安装崩溃。先切到中立目录。
- 后台子进程会继承 stdout/stderr 并占住管道，把整次调用拖到超时；启动前重定向全部 fd。

## 验证清单

改动本技能或 `assets/` 后逐项跑：

- [ ] `python assets/validate.py` —— 一条命令做完下面所有结构性检查，末行 `RESULT ALL_PASS`
- [ ] `"$QN" status` 输出版本与 `Username:`
- [ ] `"$QN" --list-models` 返回模型表（证明认证正常且未被污染）
- [ ] `-p ... --tools "" --no-session-persistence` 返回文本
- [ ] `-o json` 真调用工具：`is_error:false`、`total_credits` 非零，**且期望产物确实存在**
      （产物断言必须计入 PASS 条件；路径用 `cygpath -w` 生成并以 argv 传入，
      不要把 `/tmp/...` 拼进 Windows 路径判 `exists`，那会恒 False 并让检查漏判）
- [ ] 黑名单审计：上述保留名一个都不在清洗列表里
- [ ] `QCN_HOME=/etc "$QN" status` 必须拒绝
- [ ] 黑名单审计用 `sed -n '/^is_pollution() {/,/^}/p' | source` 后逐名调用，
      **在 bash 内直接 echo 计数**，不要把变量嵌进 `[ ]` 测试再套引号（会误报 FAIL）
- [ ] `assets/sdk_bridge.py` 跑极小任务：`"ok": true`、额度非零、产出文件存在，
      `--log` 里能看到 Write 的 `gate` 事件
- [ ] 反向验证：去掉 `env=SCRUB` 必须复现 `Control request timeout: initialize`
- [ ] 权限规则验证一律**看结果**：用模型猜不出的锚点（植入的秘密、必须读的文件），
      并保留"无规则"对照组

## 官方文档查证入口（与本正文冲突时以它为准）

全站点索引 `https://docs.qoder.cn/llms.txt`，任意页面加 `.md` 即得干净原文。**"要查什么 → 哪一页"的
映射表、`llms-full.txt` 其实是子集的假阴性警告、更新日志整读陷阱**，都在
[DOC-LOOKUP.md](assets/DOC-LOOKUP.md)。本技能正文是缓存，会过期；遇下列情形先现查再答，别凭正文断言。

## 参考资料

- ACP 线级细节与两处文档纠错：[ACP-PROTOCOL.md](assets/ACP-PROTOCOL.md)；配套客户端
  `assets/acp_drive.py`（已被 SDK 取代，只在装不上 SDK 时用）
- 文档查证映射表：[DOC-LOOKUP.md](assets/DOC-LOOKUP.md)
- 版本历史、D/C 级明细、排错顺序、方法留档、本轮实测台账：[EVIDENCE.md](assets/EVIDENCE.md) —— 会过期，
  勿据此判断当前行为。**对外发布先照其中「交接并入与发布协议」执行**（"可以公开"≠"可以推送"，两次确认）。

## 事实来源分层

只有 **V** 可当既成事实引用。

### V — 本机执行验证
- SDK 缺 `can_use_tool` → 工具静默失败；`message_uuid` 为 Rewind 唯一锚点；
  `session_store` 与 `enable_file_checkpointing` 互斥。桥接 allow 分支已实证。
- `Bash(cmd:*)` allow 规则有效（双臂 + 提交计数对照）；`--allowed-tools` 不构成授权。
- **UltraCode 两条入口都真实，且判据不是 credits**：关键词 `ultracode` 注入单轮 `workflow_keyword_request`，
  实测该臂真的调了 `Workflow` 工具（其余臂 0 次）；常驻档 = 顶层设置 `ultracode:true` 且**不传**
  `--reasoning-effort`，此时 `reasoningEffort` 自动升到 `xhigh`（不传又不设的基线是 `null`）—— 这个
  `null→xhigh` 才是可数锚。**别拿"有没有起 Workflow"当常驻档判据**：常驻提醒原文写着
  "Use the Workflow tool on every substantive task … **Solo only on conversational/trivial turns**"，
  起不起由模型裁量。但**在真实编码任务上它也不起**：一个 14 回合、动到 Bash/Read/Grep/Write/Edit
  的委派（常驻档开着、`effort=xhigh`）实测 `Workflow` 仍 0 次 —— headless 下常驻档的净效果目前只确证到
  "抬 effort"，编排仍要靠关键词单轮触发。
- 环境清洗是三通道共同前提；`sdk_invalid_args` 与 `Control request timeout: initialize`
  的因果均已复现并反证。
- 权限：`permissions.deny` 相对路径形式生效（`Edit(x)`、`Read(x)`）；**盘符绝对路径形式
  静默不匹配**；`--allowed-tools` 压不过 deny；`permission_denials` 不记录规则命中。
- CWD 即受信目录：未列入 `trustDirectories` 的工作目录中 `accept_edits` 写文件次次生效；非受信则非 default 模式强制降回 `default`，无头下表现为全部被拒。
- `rollback` = **CLI 版本回退**（`--to <version>`），不是撤销文件改动。
- **`--reasoning-effort` 的取值确实不校验，但 `ultracode` 是被特判的魔法值**：`zzz` 同样被接受，所以
  「被解析器接受」仍不等于「该特性存在」；然而 bundle 里存在对 `reasoningEffort` 字面量
  `ultracode` 的一行真特判，实测 `--reasoning-effort ultracode` 会让转写里的 `reasoningEffort` 落地成
  **xhigh** 并开启常驻档。判取值有没有被特判，看落地值，不看是否报错。
- `QODERCN_MEMORY=1` 下无头委派**未产生任何记忆目录/文件**，与"仅交互式会话生效"一致
  → 无头路径不要指望自动记忆。
- `modelUsage` 键为内部计费桶 ID（映射见「模型与计费」）。
- **`118` 按模型分布而非按命令**：同一时刻 `-m Auto` 与 `gfmodel` 三次全挂、三个 Qwen 模型三次全成功；
  读 `usage_info.py` 后可给出因果：计划池 300 已用满，Qwen 模型改扣专属日包，故只有它活着。
- **跨进程 Rewind 成立**；**`--add-dir` 扩边界成立**；**`acceptEdits` 目录内编辑不调 `can_use_tool`**。
- **`total_credits` 不能当特性探针**：同一 trivial prompt、`turns=1`、同模型的五次实测落在
  0.048 / 0.049 / 0.051 / 0.075 / **0.571** —— 12 倍抖动。因此"某特性让 credits 涨了"是**弱证据**
  （本技能早先据 0.456→1.041 判 UltraCode 就属于这类，现降为辅助证据）。要判特性是否生效，用**可数**
  观测点：`num_turns`、子代理/工具计数、磁盘产物、回复里的元叙述（关键词臂的回复主动说
  "trivial…rather than spin up a workflow"，这才是命中锚）。
- **`--remote` 不可达与 exit 42 的根因：不是网络、不是账号权益，是版本错配**。可用性探测打
  `GET /api/v4/service/region/endpoints`，该路径在服务端**恒 404**，而同进程同 IP 的 `v3` 同路径拿
  **200**；attempts 明细 `failurePhase:"http_status"`、`requestCommitted:true` —— 请求完整走完并收到
  响应，网络阶段排除。`/api/v1/remote/*` 从未被调用，故账号有无云端权益本机无从判定。终态
  `exit_code=42 reason="unknown"`，文案却是"check your network connection" —— **归因错配，看到这句
  别去查网线**（官方码表 42=输入/参数无效，`--remote` 借用该通用桶）。headless 持续 404 有 v3 兜底、不致命。
- **倍率 ≠ 币种**：Qoder CLI CN 的每日赠送是 **Qwen 专属包**，而 `/usage` 用量面板**只有交互模式有**，
  无头查不到某模型扣哪个池。本轮把推断收紧一步：非 Qwen（`gfmodel`）与 `Auto` 全部走空池（`118`）、
  Qwen 五款全部可用 —— "当前能用的"与"专属日额覆盖的"重合，但这是**反证不是直读**，仍待 `/usage` 分项。
- 三份清洗器逐名 `source` 复验，黑名单误删为 0。

### D / C — 转述级（不可当事实用）
明细移到 [EVIDENCE.md](assets/EVIDENCE.md)。**D** = 文档原文可引但未执行；
**C** = 仅见于更新日志。引用前现查或实测升级为 V。

### 源码级已证（grep 自身 bundle `qoderclicn-1.1.37.exe`；只录结论与标识符，混淆代码原文不录）
- **2026-08-30 在 1.1.37 上复验：四条全部在位**，唯一显著变化 `additionalDirectories` 42 → 76（并集结论不变）；明细计数见 EVIDENCE.md「台账补充：2026-08-30」。
- **常驻档读的是顶层键，不是 `advanced.`**：构造 config 那一段里 `bugCommand` 走 `advanced.` 嵌套读法、
  `ultracode` 走顶层读法，两者并列 —— 所以设置文件里写顶层
  `ultracode: true`；本技能先前由 `category:"Advanced"` 推断出的 `advanced.ultracode` **已被实测推翻**
  （那一臂毫无反应）。另确认常驻档仅在非 ACP 通道判定；**关键抑制项是显式 effort 覆盖**：显式传任何
  非 `ultracode` 的 `--reasoning-effort`（哪怕 `xhigh`）都会把常驻档关掉 —— 我最初四臂就是这么自己把
  自己的实验掐死的。要常驻就别同时传 effort，或者直接 `--reasoning-effort ultracode`。
- **`reasoningEffort` 的枚举是 `none|low|medium|high|xhigh|max`**（阈值 1024/8192/24576/49152），
  字面量 `ultracode` **不在枚举里、却被单独特判**成常驻档开关并把落地值改成 `xhigh`。所以
  "取值被解析器接受"依然不能当存在性证据（`zzz` 同样被接受），但反过来"不在枚举里"也不能判它无效 ——
  两头都得看落地值。本技能先前把这两条当成互证，是错的。
- **目录信任**：`trustDirectories` 与 `additionalDirectories` 在判定函数里**取并集，无优先级之争**；精确命中
  →`TRUST_FOLDER`，命中父目录→`TRUST_PARENT`，另有 `isInheritedTrustFromIde`（IDE 也能授予信任）。
  `trustDirectories` 有意只写用户级，注释明说"不被项目级覆盖"。
- **MCP 懒加载**：常量 `["mcp_list","mcp_get","mcp_call"]`；启用式 = 环境变量 `QODER_MCP_LAZY=1` 或
  设置项 `mcp.lazyLoad`，**环境变量压过设置**；`mcp_list` 列 `mcp__<server>__<tool>`、`mcp_get(toolName)`
  取 schema、`mcp_call` 执行；传 `--allowed-mcp-server-names` 会使 `mcp.excluded` 失效。

### ? — 开放问题（2026-08-29 晚单测收窄；深夜官方手册复核后仅剩产品侧两项）
1. **三旗标已单测且官方有档**（cli-reference「远程与协作」+ cloud-mode/remote-control 页）：`--remote [task]` 官方语义=云端 VM 建会话并流式回传，需登录+GitHub 授权+`/remote-env` 选默认环境（写入 `remote.defaultCloudEnvironmentId`），本机仍 rc=42（可用性探测路径 404）；`--teleport <id>`/`--remote-session <id>` 已抵达服务端 Remote session API 并收应用级 400 `InvalidSessionID`（带 request_id）——**加载 API 已上线**，缺的只是真实云端会话；`--remote-control <id>` 为无头 worker（官方），子命令 `remote-control` 是守护进程（`--spawn same-dir|worktree`、`--capacity 32`）。
2. **MCP 命名两侧独立实现**：CLI bundle 零 `qwenwork*` 字样、常量 `["mcp_list","mcp_get","mcp_call"]`；`qwenwork_mcp_tool_list/get/call` 只在 QwenWork 宿主 app.asar（17/18/22 处）——同构是同引擎表象、非互引；官方 `mcp.lazyLoad` 明说"暴露 meta 工具"，与 bundle 三常量互证；"有意对齐 QwenWork"仍待产品侧。

### 已证伪，勿再用
`!**`、`WebFetch(domain:...)` 规则写法在 CN 文档中仍不存在（国际版/OpenClaw 残留）；
`QODERCLI_PATH` 不在 **settings-reference** 变量表（Python SDK 官方名 `cli_path`），但 SDK 排障页
`cli_sdk_troubleshooting.md:19` 有载 —— 勿再说"完全未文档化"；`QODER_PAT`/`QODER_SAT` 不是 CLI/SDK 变量
（官方是 `QODERCN_PERSONAL_ACCESS_TOKEN`），但**云端侧它们确为官方写法**，勿当整体不存在；
`hooks list` 不存在（`hooks` 仅 `migrate`，实测）；`rollback` 不是文件撤销机制（`/rewind` 才是）。
**2026-08-29 深夜撤出**：`~/path` 规则写法 —— 官方 permissions.md 明文记载 `~/Documents/**`（home 相对）与 `//`（根绝对），此前"CN 文档不存在"所依据的页面集已过时。

