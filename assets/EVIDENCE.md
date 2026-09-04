# 证据分级与台账

SKILL.md 的结论按证据等级分级，本文件承载完整分级（V / D / C / 源码级 / ? / 已证伪）与逐条取证台账。除 V 级外均**不可当作既成事实使用**；引用前先按 SKILL.md「官方文档查证入口」现查，或直接实测升级为 V。下方先列 D / C 两级明细，文末「事实来源分级」节收录 V、源码级、开放问题与已证伪。

### D — `.md` 原文可引，本机未执行
CN 规则词汇 `Bash(npm run test:*)`、`Agent(general-purpose)`、会话内 `/allow` `/deny`
（落 `settings.local.json`）；`security.folderTrust.enabled`=true、`toolSandboxing`=false、
`disableYoloMode`=false、`advanced.excludedEnvVars`=`['DEBUG','DEBUG_MODE']`、
`context.fileName`=`AGENTS.md`、`memoryBoundaryMarkers`=`['.git']`、`mcp.lazyLoad`=false
（开启后仅 `mcp_list`/`mcp_get`/`mcp_call`）、`fileCheckpointing.enabled`=true；
未受信目录不加载 Rules/Hooks/MCP/AGENTS.md；`/goal --turns`+`/goal resume`、
`/loop [interval] <prompt>`；SDK `QoderCliProcessError`；`mcp add/list/remove` 语法。

### C — 仅见于更新日志（**2026-08-30 全站对账后四项已升 D**）
更新日志本身就是文档站正式页面 `product-overview/qoder-cn-cli.md`，下面四项均有行号可引，"当前文档页查无"
的说法作废：子代理默认 150 轮（:468）；技能远端 HTTPS 安装与 `-s/--scope`（:660）；插件
`PLUGIN_ROOT`/`PLUGIN_DATA`（:1682）；`mcp auth` 子命令（:22）。
（UltraCode 的常驻形式已在本轮升级为源码级证据：设置项是**顶层** `ultracode`，嵌套的
`advanced.ultracode` 已被实测推翻，它从来不是旗标。）



---

---

## 版本与运行时（会过期，用前现查）
- 版本钉子是易失的：本机曾在 1.1.34/1.1.37 间反复。任何版本相关断言以 `"$QN" --list-models` 与 `docs.qoder.cn/llms.txt` 现查为准。
- 内置 SDK 运行时版本偏旧（曾 1.1.23），务必用 `cli_path` 钉住自己的安装；`QODER_SKIP_VERSION_CHECK` 可跳版本校验。
- JetBrains 插件另走一套 Go 守护进程（`--httpPort 37510` / `--socketPort 37010`），登录存储与 CLI 不互通，非 IDE 下其 `version` 会 panic。它会向拉起的 CLI 注入 `QODER_WORKING_DIR`、`QODER_MCP_CONFIG`、`QODER_APPEND_SYSTEM_PROMPT`、`QODER_PORT`、`QODER_TERMINAL_SHELL`、`QODER_SDK_ACCESS_TOKEN`、`JB_IDE` 等，其中若干同时是合法 CLI 配置——光凭名字分不清是用户本意还是另一台 IDE 的残留，故委派后用 `"$QN" status` + 显式 `-w` 兜底。

---

## 官方码表（现查为准）
- **SDK error_code**：105 认证过期 / 110 当日限额 / 113 配额耗尽 / 114 免费试用 / 115 免费用户 / 116 团队管理员 / 117 团队成员 / **118 个人 Credits 耗尽** / **119 所选模型免费额度** / 122 Billing Group / 406 敏感内容 / 416 范围 / 430 能力不支持 / **47902 最大轮数** / 48716 Hook 阻止 / 80411 输入过长 / 80412 附件过多 / 500·10408·10500·10605 排队·100400-100403 BYOK。官方 118=个人池（账号级），模型级配额是 119。
- **CLI 进程退出码**：0 / 1 通用 / **41 认证失败** / **42 输入或命令行参数无效** / 44 沙箱致命 / 52 配置致命 / 53 轮数致命 / 54 工具致命 / 130 取消。`--remote` 借用 42 通用桶。

---

## 排错顺序

按此顺序排查，跳步会误判：

```
- [ ] 1 报 sdk_invalid_args 或 Control request timeout → 环境未清洗（不是缺旗标、不是认证）
- [ ] 2 QoderAuthError 提及 token → 查 QODERCN_PERSONAL_ACCESS_TOKEN 是否残留失效值
- [ ] 3 status 看不到登录 → 确认 ~/.qoder-cn/.auth 存在（Go 守护进程是另一套存储）
- [ ] 4 模型不符预期 → 看 modelUsage 桶名对照内部 ID，别当"没切换"
- [ ] 5 恢复会话失败 → cwd 与 project key 是否一致
- [ ] 6 deny 规则像没生效 → 规则是否用了盘符绝对路径；改用相对形式并按结果复核
- [ ] 7 秒退且 turns=1/credits=0/<synthetic>/stderr 空 → 读 errors[]；多半 error_code=118（该模型池空），
      换 --list-models 里的模型；Auto 与非 Qwen 同属已耗尽的通用池
- [ ] 8 回调一次没触发但文件写成功了 → permission_mode 是 acceptEdits 且目标在 cwd 内（正常，不是坏了）
- [ ] 9 想知道还剩多少、扣哪个池 → python assets/usage_info.py（零 credits；SDK 会漏掉 Qwen 专属包，脚本已补）
- [ ] 10 想确认某个旗标/档位真抵达了会话 → 读该 run 日志里的 [session.runtime_config] 行，别拿 credits 反推
```


---

## 方法留档

**委派型调查必须"先交报告、再展实验"**：一次 5 题、45 回合的委派把预算全花在探针上（5 个 probe 目录、
42 条受管请求、6.51 credits），会话结束前没写报告；事后用 `resume` 补写又遇 `exit code 42`。最后靠**读它
落盘的会话转写**（`~/.qoder-cn/projects/<project-key>/<session_id>.jsonl`，assistant 文本段可直接抽出来）
才拿回结论。以后：要求第一段输出就是结论骨架，或把每题拆成独立小委派。

`llms-full.txt` 是**子集**，参考类页面（settings-reference、permissions、mcp-reference）不在其中，用它做
全量核对必然假阴性 —— 必须逐页取 `<url>.md`。核对名单一律 `source` 出实现里的判定函数逐名调用，不要手抄
名单、不要把 bash case-glob 转译成正则。验证权限类断言只看结果并保留对照组，**不要把结果文本截断后再下结论**
（本轮就因此丢了一次本可判定的证据）。多补丁脚本须**先预检全部锚点再落盘**，否则中途断言失败会让已完成的
部分改动一起丢失（本轮实际发生两次）。

---

---

## CN 规则词汇原文（D 级，转述自 cli/permissions.md 与 cli/memory.md）
### CN 的规则词汇（`cli/permissions.md` 原文，本机未逐条执行）

CN 文档里出现的规则形式是 `Bash(npm run test:*)`、`Bash(npm publish:*)`、
`Agent(general-purpose)`（子代理名匹配不分大小写），以及会话内 `/allow` `/deny`
写入 `settings.local.json`。**没有** `~/path`、`!**`、`WebFetch(domain:...)` 这些**可信目录规则（此前记为"文档与实测矛盾"，实为我漏读一句，已解除）**：
`cli/permissions.md` 写明 **Qoder 把运行时 CWD 直接视为受信目录**；非默认权限模式只在
受信目录生效，不受信时强制降回 `default`；`security.folderTrust.enabled` 默认 `true`。
本机多次在不在 `trustDirectories` 名单里的 Temp 目录用 `accept_edits` 写文件成功 ——
那些目录**就是**工作目录，与文档不冲突。真正的边界在**工作目录之外**；`cli/memory.md`
另有同族规则：未受信目录不加载 Rules、Hooks、MCP 与 `AGENTS.md`。扩边界用 `--add-dir`
（= `permissions.additionalDirectories` / `/add-dir`，实测生效）。
判定操作是否真成功，只看**产物是否存在**，别只看 `is_error`。

收紧边界的正确做法：项目文件里写 `permissions.deny` + 让目标处于真实 git 仓库内；
把 `--allowed-tools` 当便利授权清单，不当作边界。

---

## 交接并入与发布协议

- **发布协议（技能已公开，改动即涉及推送）**。公开仓：`https://github.com/<你的账号>/qodercn-cli`
  （public，main）。**git 历史无法事后脱敏**，所以首次进入 commit 的内容就必须是干净的 —— 宁可多扫一遍。
  1. **A 本地改动**：只改 `SKILL.md` / `assets/`，改完 `python assets/validate.py` 必须 `ALL_PASS`。
  2. **B 脱敏扫描（只读，不改文件）**：逐项出命中清单 + 建议替换，扫描对象是待公开的全部文件。
     命中类别：Username、账号 uid、额度包 ID（`act-YYYYMMDD-NNN`）、本机绝对路径（含 `C:\Users\...`、
     `~/.qoder-cn` 之外的用户目录痕迹）、以及 bundle 混淆源码字面（压缩后的单字母变量名与表达式原文）
     —— 这些一律**改写成结论转述**，不保留原文；**禁令示例本身也不许引用真实片段**。
  3. **C 第一次确认**：把 B 的命中清单 + 一句话变更摘要交给用户，**得到明确同意之前不得公开**。
  4. **D 推送（需再次点头）**：clone 放在**技能目录之外**（如工作区），流程是"技能目录 → 复制脱敏内容
     → clone → commit → push"。技能根目录因此不出现 `.git`，保持只有 `SKILL.md`、`.skill-metadata.yaml`、
     `assets/` 三样。
  5. **E 回核**：推完把 commit 与远端地址回给用户核对。
  确认点是两个、彼此独立：**"可以公开"与"可以推送"不是一次授权**。

- **云端三旗标已单测（收窄我原先的概括）**：`--teleport <id>` 与 `--remote-session <id>` 能抵达服务端
  Remote session API，返回**应用级 400 `InvalidSessionID` + request_id** —— 说明**该接口已上线**，
  "服务端未上线 v4" 的判断**只对 `--remote` 的可用性探测路径成立**，不能外推到整条云通道。
  `--remote <任务>` 建新会话仍 `rc=42`；`--remote-control <id>` 是无头 worker 入口，子命令
  `remote-control` 是守护进程（`--spawn same-dir|worktree`、`--capacity 32`）。真正用起来还缺一个
  真实云端会话 id（被 `--remote` 卡住）。
- **MCP 三段式两侧独立**：CLI bundle 内 `qwenwork*` 出现 **0 次**，而 `qwenwork_mcp_tool_list/get/call`
  只存在于 QwenWork 宿主 `app.asar`（17/18/22 处）→ 可排除互相引用；"是否有意对齐"只剩同引擎同构
  这一层推测，且不再是使用阻塞。
- **取证档案归置（2026-08-30）**：21 处不一致审计与 `--remote` 取证的原始文件在旧会话 outputs
  （`remote不可达取证.txt`、`独立复核-21处不一致正文.txt`、`独立复核-阶段1骨架.txt`、一份墓碑交接 md）。
  **不并档进本仓**：内含本机绝对路径、真实 IP、bundle 混淆源码原文，按协议 B 不得进公开仓；需要细节时按
  路径回读原文。从档案回收进正文/台账的增量：workflows auth-token 超时按 run 分布集中在凌晨 01:1x 与
  04:1x 两簇（共 39 run）；feature-gates 全名单（`echo`、`cloud_remote`、`context_window_selection`、
  `httpdns`、`model_stream_diagnostics`、`model_server_transport`、`model_stream_timeout`、
  `sse_body_null_diagnostics`、`workflows`、`cli_promotion`、`codebase_backflow`、`dynamic_commands`、
  `model_retry_after_payload`、`auto_memory`、`prompt_policy`、`auto_memory_policy`、`auto_dream`、
  `legacy_infer_domain_failover`）；三旗标同传 `--no-session-persistence` 的报错原文
  `--no-session-persistence can only be used with --print mode`；官方码表补录 **110=当日限额、113=配额耗尽**
  （正文贴线移出）；`-p` 信封 `is_error`/缺 `result` **不等于任务本身失败**（判成败看产物，正文该句被
  官方锚替换后移此保存）；`cli/installation.md` 要点见 DOC-LOOKUP.md 映射表新行。
- **历史重写（2026-08-30，终态=单一全新提交）**：初始提交曾把三类内容带上公开仓 —— 网关 IP `47.x.x.x`、
  账号套餐标识、额度包日期号 `act-2026<日期>`。多轮逐提交掩码后发现中间提交自带的历史快照无法自抹
  旧引用，遂放弃保链，全部工作压成**一个全新提交**，旧链整体弃用、远端删 ref 后重推。正文掩码为
  `47.x.x.x` / `<trial-plan>` / `act-<date>`，终态仓库逐对象复验零隐私、零旧提交号。
  **旧提交号刻意不录于任何文件** —— 远端 GC 前旧对象仍可按 SHA 直取，写出来等于留取货单。
  **教训：git 历史重写不要在沙箱挂载盘上跑** —— `git-filter-repo` 会在 `repack`/`config.lock` 处因
  9p 挂载不支持 rename+chmod 而**报"Completely finished"却零改写**（`commit-map` 里 old==new 是唯一露馅处）；
  改用 `git filter-branch --tree-filter` 并把仓库 `cp -a` 到 `/tmp`（原生 tmpfs）后才真正生效。另：`/tmp`
  不跨工具调用存活，重写→验证→`bundle` 必须串成单次调用。

---

---

### 待下轮收的缺漏（文档有、技能缺，价值最高五条）
1. `--worktree <name>` 独立 Git 工作树跑并发委派（`cli/parallel-tasks.md:15-27`），落在
   `<repo>/.qoder/worktrees/<名>`，`.worktreeinclude` 带未跟踪文件；技能完全没写。
2. `get_context_usage()` 零回合读上下文实况（`cli/sdk/cost-usage.md:18`）：分类估算、自动压缩状态、
   重复文件读取、每个 skill 占比 —— 与 `usage_info.py` 互补，一个读额度一个读上下文。
3. SDK 入向插话 `priority="now"/"later"/"next"` + `should_query=False` + `interrupt()`
   （`cli/sdk/multi-turn-conversation.md:113-121`）；带 `message_uuid` 才能 `cancel_async_message` 撤回。
4. 工作流落盘 `.qoder/workflows/*.js`（项目级压过插件级与内置），脚本无 shell/fs/网络权限、副作用全走子 Agent
   （`cli/workflows.md:100-155`）。
5. 云端 Session 状态机：向 `processing` 发消息 `409`、cancel 对 `idle` 是空操作、只有 `archived` 是终态、
   `usage.total_credits` 是累计快照要按 id 覆盖（`cloud-agents/sessions.md:287,313,329`）。

---

## 事实来源分级（V / 源码级 / ? / 已证伪）

SKILL.md 结论按下列等级分级，只有 **V** 可当既成事实引用；本节各条对「模型与计费」「验证清单」等小节的引用均指 SKILL.md 对应小节。

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
- 清洗名单（`qcn.sh` + `sdk_bridge.py`）逐名 `source` 复验，黑名单误删为 0。

### D / C — 转述级（不可当事实用）
完整明细见本文件顶部「证据分层：D / C 级明细」。**D** = 文档原文可引但未执行；
**C** = 仅见于更新日志。引用前现查或实测升级为 V。

### 源码级已证（grep 自身 bundle `qoderclicn-1.1.37.exe`；只录结论与标识符，混淆代码原文不录）
- **2026-08-30 在 1.1.37 上复验：四条全部在位**，唯一显著变化 `additionalDirectories` 42 → 76（并集结论不变）；明细计数见本文件「台账补充：2026-08-30」。
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
`cli/sdk/troubleshooting.md:19` 有载 —— 勿再说"完全未文档化"；`QODER_PAT`/`QODER_SAT` 不是 CLI/SDK 变量
（官方是 `QODERCN_PERSONAL_ACCESS_TOKEN`），但**云端侧它们确为官方写法**，勿当整体不存在；
`hooks list` 不存在（`hooks` 仅 `migrate`，实测）；`rollback` 不是文件撤销机制（`/rewind` 才是）。
**2026-08-29 深夜撤出**：`~/path` 规则写法 —— 官方 permissions.md 明文记载 `~/Documents/**`（home 相对）与 `//`（根绝对），此前"CN 文档不存在"所依据的页面集已过时。
