# 证据分层：D / C 级明细

本文件是 SKILL.md「事实来源分层」里 **D（文档原文可引，未执行）** 与 **C（仅见于更新日志）** 两级的完整明细。两级都**不可当作既成事实使用**；需要引用前先按 SKILL.md 的查证入口现查，或直接实测升级为 V。

### D — `.md` 原文可引，本机未执行
CN 规则词汇 `Bash(npm run test:*)`、`Agent(general-purpose)`、会话内 `/allow` `/deny`
（落 `settings.local.json`）；`security.folderTrust.enabled`=true、`toolSandboxing`=false、
`disableYoloMode`=false、`advanced.excludedEnvVars`=`['DEBUG','DEBUG_MODE']`、
`context.fileName`=`AGENTS.md`、`memoryBoundaryMarkers`=`['.git']`、`mcp.lazyLoad`=false
（开启后仅 `mcp_list`/`mcp_get`/`mcp_call`）、`fileCheckpointing.enabled`=true；
未受信目录不加载 Rules/Hooks/MCP/AGENTS.md；`/goal --turns`+`/goal resume`、
`/loop [interval] <prompt>`；SDK `QoderCliProcessError`；`mcp add/list/remove` 语法。

### C — 仅见于更新日志（**2026-08-30 全站对账后四项已升 D**）
更新日志本身就是文档站正式页面 `product-overview_qoder-cn-cli.md`，下面四项均有行号可引，"当前文档页查无"
的说法作废：子代理默认 150 轮（:468）；技能远端 HTTPS 安装与 `-s/--scope`（:660）；插件
`PLUGIN_ROOT`/`PLUGIN_DATA`（:1682）；`mcp auth` 子命令（:22）。
（UltraCode 的常驻形式已在本轮升级为源码级证据：设置项是**顶层** `ultracode`，嵌套的
`advanced.ultracode` 已被实测推翻，它从来不是旗标。）



---

## 版本与历史（会过期，用前现查）



本机 CLI 1.1.34；SDK 1.0.13 且内置运行时 1.1.23（早于 1.1.27 失效 PAT 可诊断报错、
1.1.28 `acceptEdits` 放行 MCP 修复、1.1.30 `--max-turns` 生效修复）。JetBrains 插件另走
一套 Go 守护进程（`--httpPort 37510` / `--socketPort 37010`），登录存储与 CLI 不互通，
非 IDE 下其 `version` 会 panic。插件会向它拉起的 CLI 注入 `QODER_WORKING_DIR`、
`QODER_MCP_CONFIG`、`QODER_APPEND_SYSTEM_PROMPT`、`QODER_PORT`、`QODER_TERMINAL_SHELL`、
`QODER_SDK_ACCESS_TOKEN`、`JB_IDE` 等，其中若干同时是合法 CLI 配置 —— 光凭名字分不清
是用户本意还是另一台 IDE 的残留，故委派后要用 `"$QN" status` + 显式 `-w` 兜底。




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

## 台账：2026-08-29 那轮（CLI 1.1.34 / SDK 1.0.13 / model.name=Qwen3.8-Flash）

极小单回合任务（`-p "Reply with exactly: PROBE_OK" --max-turns 2`）逐模型实测：

| 传入 `-m` | 结算桶 | is_error | credits | 备注 |
|---|---|---|---|---|
| 省略（当时 `gfmodel`） | `<synthetic>` | true | 0 | error_code=118，stderr **空** |
| `Auto` / `auto` | `<synthetic>` | true | 0 | 3/3 复现，被识别但池空 |
| `gfmodel` | `<synthetic>` | true | 0 | 同上 |
| `Qwen3.8-Flash` | `qfmodel` | false | 0.0466–0.0469 | 3 次样本；延迟 12–81s |
| `Qwen3.7-Flash` | `q37fmodel` | false | 0.1132 | |
| `Qwen3.8-Max` | `qmodel_38max` | false | 0.5628 | |
| `Qwen3.7-Plus` | `qmodel` | false | 1.1337 | |
| `__NOPE__` | `qmodel_38max` | false | 0.05 量级 | stderr 警告 + 回落账号默认 |

其它同轮记录：写文件任务（2-3 回合）0.21–0.73 credits；跨进程 Rewind 的 A 阶段一次真实模型失误 —— 要求写
`NEW-CONTENT`，模型写成 `NEW-CO`（便宜模型截断字面量），**因此 xproc_rewind.py 的断言只要求"内容变了"而
不要求等于指定串**。`errors[]` 原文：`You've reached your credit usage limit. Please upgrade your
subscription plan to get more resources. Report Issue (input /feedback)`。

### 台账补充：2026-08-29 下午（额度读数打通后）

`usage_info.py` 实读结果（账号套餐：试用档，uid 已略）：

- 计划池 `userQuota`：`total=300 used=300 remaining=0 pct=100`，`isQuotaExceeded=true`，
  `expiresAt=2026-09-12 01:16`（计划/试用周期，**不是日额**）。`addOnQuota`、`orgResourcePackage` 均不存在。
- 被 SDK 丢掉的 `dedicatedResourcePackages`：旧专属包（`act-<日期>-<短id>`），`total=500 used=13 remaining=487`，
  `expiresAt=2026-08-30 10:00`，`available=true`，中文标签原文
  **"Qwen 专属积分：在模型选择器中选择 Qwen 系列模型时优先抵扣该积分。"**
- 同日日志里可见计划池从 `used=0` → `2` → `7` → `300` 的全过程，即本会话委派把它打满的轨迹。
- 结论链：非 Qwen 模型与 `Auto` 走计划池 → 池空即 `118 personalCreditsDrainedOut`；Qwen 模型优先走专属
  日包 → 仍可用。专属日包优先抵扣，故仍可用。GUI 与 API 数字完全对上（300/300、13/500、9 月 12 日），证实两者同账号同后端。

- **两个"刷新时刻"互相矛盾，未判**：API payload 里旧专属包的 `expiresAt` 解出 `2026-08-30 10:00`，
  而桌面 GUI 显示"Qwen 专属积分 13/500，**明早 8 点刷新**"、"套餐内 Credits 300/300 已用完，9 月 12 日刷新"。
  能同时成立的解释是 **08:00 发放新包、旧包 10:00 过期**（有效期约 26 小时）。
  判据：08-10 点之间跑一次 `usage_info.py` —— 若同时出现 `act-<当日>-*` 新包且旧包仍在列表 = 两个时刻成立；
  若只有新包 = 我解日期时把某个 UTC 戳算错了。**不要拿"10:00"当可用窗口去排任务。**
- credits 抖动实测（同 prompt、`turns=1`、`-m` 省略=Qwen3.8-Flash）：0.0483 / 0.0494 / 0.0506 / 0.0527 /
  0.0751 / **0.5706**。极小任务的地板值约 0.05，别用均值判涨跌。

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

- **常驻 Ultracode 五臂台账**（同一个"读 src.py 写 REVIEW.md"任务，锚点 = 转写 `tool_use` 计数 +
  `runtime-config` 的 `reasoningEffort`）：

  | 臂 | effort 传值 | 设置 | reasoningEffort 落地 | Workflow 调用 | credits |
  |---|---|---|---|---|---|
  | 关键词 | 不传 | 无 | null（关键词不改 effort） | **1** | 0.934 |
  | `advanced.ultracode` | xhigh | 嵌套键 | xhigh | 0 | 0.340 |
  | 顶层 `ultracode` + xhigh | xhigh | 顶层键 | xhigh | 0 | 0.435 |
  | B1 `--reasoning-effort ultracode` | ultracode | 无 | **xhigh** | 0 | 0.461 |
  | B2 顶层 `ultracode`，不传 effort | 不传 | 顶层键 | **xhigh** | 0 | 0.441 |
  | control | xhigh | 无 | xhigh | 0 | 0.269 |

  定论来自 B2：**不传 effort 的基线是 `null`，B2 不传 effort 却拿到 `xhigh`** —— 顶层 `ultracode:true`
  确实被读到并生效。本轮全部 Ultracode 实验（三臂 + 长臂 + 两臂加测）实耗 **5.0 credits**：依据是 usage_info 前后两次一手读数 `used=13 → used=18`，不做手工相加（手加会漏掉失败臂与协议开销，我第一版就漏成 2.9）。

- **`--remote` 定论取证（16:50 两次复现，零 credits）**：`v3/service/region/endpoints` → 200
  （带 `serverRequestId`）；`v4/service/region/endpoints` → 404（`serverRequestId=<unknown>`），
  attempts 原文 `{"ip":"47.x.x.x","status":404,"failurePhase":"http_status",
  "errorCode":"404","requestCommitted":true,"nextAction":"surface_to_user"}`。裸 curl 无区分力
  （不带 CLI 的 httpdns + 请求头时，连 v3 也一律 503 由 ALB 拒绝），所以只能在 CLI 内部对照。
  另更正一处过度概括：`[workflows] Timed out waiting for auth token before feature gate registration`
  实测覆盖 **39 / 313** 个 run，不是每个无头 run 都有，也与本次 Ultracode 五臂结论无关。

- **委派型任务的成本标定点（Qwen3.8-Flash，常驻档 ON）**：一次 14 回合真实编码委派（读文件 + 写
  `assets/validate.py`，Bash 7 / Edit 4 / Write 1 / Read 2 / Grep 2 / Glob 1）= **3.443 credits**，
  约 0.25 credits/回合。被 `--max-turns 14` 掐断故 `is_error=true` 且无 `result`，但产物完整落地 ——
  再次说明"信封报错 ≠ 任务失败"，判成败看产物。`Workflow` 调用 0 次。

---

## 台账补充：2026-08-29 晚（三旗标单测 + bundle grep 复核 + MCP 命名取证）

- **三旗标单测**（全程零 credits）。`--help` 43-48 行实载：`--remote [task]`、`--remote-session <id>`、
  `--teleport <id>`、`--remote-control <id>`；子命令 `remote-control` = 守护进程（`--name`、
  `--spawn same-dir|worktree`、`--capacity 32`、`--directory`、`--verbose`）。实测：
  ① `-p` 与三旗标同传时再带 `--no-session-persistence` 会 rc=1
  `--no-session-persistence can only be used with --print mode`（三旗标使该运行按非 print 处理）；
  ② `--remote` 对照臂复现 rc=42 + "check your network connection"；
  ③ `--teleport` / `--remote-session` 不带 id、或带格式合法的假 UUID，都收到**服务端应用级**
  400 `InvalidSessionID`（含 request_id）—— **远端会话加载 API 已上线**，旧结论"服务端未上线、版本错配"
  只对可用性探测路径（`/api/v4/service/region/endpoints` 恒 404，即 `--remote` 建新会话的前置检查）成立；
  ④ `--remote-control` 无 id rc=1 `argument missing`（首测空 stderr 系与 `-p` 组合所致）。
  下一步阻塞点：要 teleport 得先有一个真实云端会话，而建会话仍被 `--remote` 卡住。
- **bundle grep 独立复核**（`qoderclicn-1.1.34.exe`，163MB，单遍 `grep -aoE`）。四条源码级结论字面全部在位
  （混淆代码原文不录，结论转述见 SKILL.md「源码级已证」）：ultracode 顶层键与 `advanced.` 嵌套 `bugCommand`
  并列；`ultracode` 特判把 effort 落地成 `xhigh` 并开常驻档；常驻档被任何显式非 `ultracode` effort 抑制；
  常驻档仅非 ACP 通道判定。枚举 `"none","low","medium","high","xhigh","max"` ×3，阈值 49152/24576 ×4；
  `trustDirectories` ×9 / `additionalDirectories` ×42 / `TRUST_FOLDER` ×3 / `TRUST_PARENT` ×4 /
  `isInheritedTrustFromIde` ×5；meta 工具常量数组与"环境变量压过设置"的启用判定；`allowed-mcp-server-names` ×2。
- **MCP 命名取证**：CLI bundle 内 `qwenwork`（不分大小写）**0 次**；`qwenwork_mcp_tool_list/get/call`
  只出现在 QwenWork 宿主 `C:\Program Files\QwenWorkCN\1.0.1-26082607\resources\app.asar`
  （17/18/22 处）。两侧命名各自实现、互不引用；宿主自带 `resources/bin/qoderclicn.exe`（strings 提示
  1.1.26 附近，迟于本机 1.1.34，与"内置运行时偏旧"一致）。

---

## 台账补充：2026-08-29 深夜（官方手册 docs.qoder.cn 全文对照）

> 依用户要求通读官方"给大模型读的手册"（llms.txt 全站索引 + 逐页 `.md` 原文），与技能正文逐条对照。
> 共取 15 页：cli-reference / settings-reference / settings / permissions / cloud-mode / remote-control /
> usage / undo-restore / hooks-reference / models / run-in-scripts / security / slash-reference / memory /
> sdk（overview / authentication / permissions / errors / references-python）+ 更新日志（定向）。
> 以下 D 级条目引用前仍需按 DOC-LOOKUP.md 现查；只有本节标"实测"的才算 V。

### 版本与更新日志
- **版本钉子已过期（2026-08-30 本机升到 1.1.37）**：原先记的"1.1.34 仍是最新版、源码级四条无需重跑"作废。
  本轮已直接 grep `qoderclicn-1.1.37.exe` 复验：四条**全部在位**，计数与 1.1.34 几乎一致 —— 枚举
  `"none","low","medium","high","xhigh","max"` ×3、`"disabled","none"` 别名 Map ×1、`max:65536` 阈值 ×1、
  `trustDirectories` ×9、`TRUST_FOLDER` ×3、`TRUST_PARENT` ×4、`isInheritedTrustFromIde` ×5、
  `["mcp_list","mcp_get","mcp_call"]` ×1、`QODER_MCP_LAZY` ×2、`lazyLoad` ×12、`ultracode:` ×12、
  `isUltracodeActive` ×10、`getUltracode` ×8、`"ultracode"` ×7。**唯一显著变化：`additionalDirectories`
  42 → 76**（并集判定结论不变）。顶层设置键 `ultracode` 仍不在 settings-reference（全文 0 命中）→ 源码级定性维持。
- **`--list-models` 在 1.1.37 返回 13 款**（原为 Qwen 五款）：`Auto`、Qwen3.8-Max/Flash、Qwen3.7-Max/Plus/Flash、
  DeepSeek-V4-Pro/Flash、GLM-5.3、GLM-5.3-Flash、GLM-5.2、Kimi-K2.7-Code、MiniMax-M2.7。文档 `cli_models.md:27-35`
  的表与本机输出不一致（文档含 Qwen3.6-Flash、止于 GLM-5.2），且全站 553 页 **0 命中 `gfmodel` 与 `GLM-5.3`**
  → "gfmodel 按文档为 GLM-5.3-Flash" 一句已降级为本机推断，13 款的新桶名待重测。
- 更新日志另证：`security` 子命令自 1.1.14 支持无头安全扫描；`--config-dir` 自 1.0.33；
  `QODER_CLI_MAX_CONCURRENT_SUBAGENTS`（1.1.31）**不在 settings-reference 变量表，但更新日志
  `product-overview_qoder-cn-cli.md:52` 明文记载**（"新增子智能体并发数限制，可通过该环境变量配置"）
  —— 旧表述"存在但未文档化"过重，改为"未进变量表"。
- **UltraCode 官方有档**（更新日志 1.1.32，2026-08-27）："/effort ultracode 命令或 ultracode 关键词触发
  Workflow 多 Agent 编排" → C 级升 D 级；与 bundle 特判（对 `reasoningEffort` 字面量 `ultracode` 的
  单独判定 + 常驻档激活要求 effort 落地 `xhigh`，本次 grep 又见）互证。
  顶层设置键 `ultracode` 本身仍只存在于 bundle（settings-reference 全文无此键），维持源码级定性。

### 与技能 V 级结论的冲突及处置
1. **CLI `--permission-mode` 大小写不敏感（新实测，V）**：`--permission-mode acceptEdits` 与 `yolo`
   均被解析（`--list-models` 正常返回，零 credits）；非法值报
   `Invalid values: … Choices: "default","plan","auto","bypass_permissions","accept_edits","dont_ask"` ——
   解析器有六枚举 + 别名归一（官方 permissions.md 明说"支持多种命名格式（大小写不敏感）"）。
   **技能旧结论"CLI 旗标是 snake_case、混用静默失效"已修正**（SKILL.md 通道/SDK 节）；SDK 选项
   camelCase 标准不变（references-python 明言 "Python SDK 使用 snake_case 字段名" 指字段名而非模式值，
   TS 模式表为 camelCase，Python 示例传小写字符串 `"default"`/`"plan"`）。
2. **`~/path` 规则写法撤出已证伪清单**：官方 permissions.md「文件访问规则」明文记载
   `~/Documents/**`（home 相对）与 `//tmp/data/**`（`//` 前缀=根绝对）。此前"CN 文档不存在"系依据旧页面集
   （疑为 llms-full.txt 子集假阴性，恰是 DOC-LOOKUP.md 警告过的坑）。`!**`、`WebFetch(domain:...)` 本页
   仍无 → 维持已证伪。
3. **`~/.qoder-cn/AGENTS.md` V/D 冲突待裁决**：官方 memory.md 把它列为用户级静态记忆位置
   （"当前用户跨项目通用偏好"），而本技能实测未加载。未重测（需一次 ~0.05 credit 的 -p 探针）；
   SKILL.md 已就地标注冲突。裁决前继续以项目级为准。
4. **bundle 枚举 vs 文档 8 档**：文档 reasoningEffort 列 `disabled/off/none/low/medium/high/xhigh/max`；
   本次 grep 实见六核心枚举数组 + 别名 Map（`disabled→none` 等）+ 阈值表（`none:0` 递增到 `max:65536`）——
   六核心 + 别名映射，两边不矛盾。

### 官方文档补充的 D 级要点（按对委派工作的重要性排序）
- **云模式（cloud-mode.md）**：`--remote` = 云端 VM 建会话 + 输出流式回传本地；Ctrl+C 仅断开订阅、云端继续跑；
  需登录 + GitHub 授权；`/remote-env` 选默认环境写入顶层设置 `remote.defaultCloudEnvironmentId`；
  官方自认已知坑："报 `Cannot find package` 错误请改用 Cloud Agents HTTP API"。
- **remote-control.md**：两条官方路径 = 会话内 `/remote-control`（本地任务远程监听，`stop`/`status` 子命令）
  与守护进程 `qodercn remote-control`（手机端直接发任务）；Web 控制台 qoder.cn/agents。与单测结论互证。
- **SDK errors 页错误码表**（官方）：105 认证过期 / 110 当日限额 / 113 配额耗尽 / 114 免费试用 / 115 免费用户 /
  116 团队管理员 / 117 团队成员 / **118 个人 Credits 耗尽** / **119 所选模型免费额度** / 122 Billing Group /
  406 敏感内容 / 416 范围 / 430 能力不支持 / 47902 最大轮数 / 48716 Hook 阻止 / 80411 输入过长 / 80412 附件过多 /
  500·10408·10500·10605(排队)·100400-100403(BYOK)。**官方 118=个人池（账号级），模型级配额是 119** ——
  本技能观察到的"118 按模型分布"是 Qwen 专属包兜底造成的表象，机制表述已在 SKILL.md 校准。
- **CLI 进程退出码（官方）**：0 / 1 通用 / **41 认证失败** / **42 输入或命令行参数无效** / 44 沙箱致命 /
  52 配置致命 / 53 轮数致命 / 54 工具致命 / 130 取消。`--remote` 的 rc=42 是借用"参数无效"通用桶（SKILL.md 已注）。
- **SDK 认证（authentication.md）**：三种官方方式 = PAT（`QODERCN_PERSONAL_ACCESS_TOKEN`，
  `access_token_from_env()`）/ Service Account（key 换短期 SAT，exchange 端点
  `https://openapi.qoder.sh/api/v1/serviceToken/exchange`，scopes 例 `models.read chat.completions`）/
  `qodercli_auth()` 复用本机登录态。技能 SDK 要点 #1 的 `qodercli_auth()` 描述与官方一致；
  `options.env` 同名变量优先于进程环境（官方明文）。
- **SDK bypass 双重确认（官方新知，已写进 SKILL.md 要点 #4）**：`bypassPermissions`/`yolo` 必须同时传
  `allowDangerouslySkipPermissions`（TS）/ `allow_dangerously_skip_permissions`（Py）。
- **Python SDK 参考（references-python.md）**：`QoderAgentOptions` 全字段 snake_case（`cli_path`、`env`、
  `max_turns`、`can_use_tool`、`settings`、`add_dirs`、`hooks`、`enable_file_checkpointing` 等与
  sdk_bridge.py 用法一致）；**AgentDefinition 反用 camelCase**（`disallowedTools`、`mcpServers`…）——
  混用陷阱；`QoderSDKClient.get_usage_info()` 官方存在（usage_info.py 的备选路径，未测）；
  `proxy` 选项未设置时不继承代理环境变量。
- **权限管道（permissions.md）**：决策序 = deny → 工具安全检查 → ask 规则 → allow/模式 → 运行环境消费
  （TUI 弹窗 / headless 自动拒 / SDK canUseTool / ACP requestPermission）；8 层规则来源优先级；
  PreToolUse/PermissionRequest Hook 可覆盖权限（**bypass_permissions 下 Hook deny 仍生效**）；
  `security.disableYoloMode` 可组织级禁 YOLO（子代理 bypass 声明降级 acceptEdits）；
  受保护路径（.git/.vscode/.mcp.json/shell 启动文件…）与 Windows 路径形状（UNC/WSL/ADS/8.3/设备路径）单独设防。
- **配置（settings.md）**：默认值 < 用户 < 项目 < 本地 < `--settings`；深度合并，**部分数组（禁用/排除类）并集合并**
  （与 bundle 的 trustDirectories 并集发现同向）；**未信任目录不加载项目/本地设置**；settings.json 支持 `//` 注释。
- **记忆（memory.md）**：rules 前缀 `.qoder/rules/**/*.md`（项目）与 `~/.qoder-cn/rules/`（用户），frontmatter
  `trigger: always_on|manual|model_decision|glob`（+ `alwaysApply`/`paths` 兼容），gitignore 风格匹配；
  AGENTS.md 支持 `@path` 导入（项目边界外需批准）；**自动记忆"只在交互式会话中运行"**（官方明文，
  与本技能无头零记忆实测一致；QODERCN_MEMORY / QODERCN_MEMORY_USER 已入官方变量表）。
- **MCP**：settings `mcp.lazyLoad`（"懒加载 MCP 工具（暴露 meta 工具）"）+ `QODER_MCP_LAZY=1` 均入官方文档，
  与 bundle 三常量 `["mcp_list","mcp_get","mcp_call"]` 互证。
- **usage.md**：官方用量面板口径 = 套餐 / 附加额度 / 组织资源包 + 80%/95% 颜色阈值；**未提专属日包、未提按模型费率**
  —— `dedicatedResourcePackages` 仅存于 API 层的判断不变，明早 08:00-10:00 判据实验照旧。
- **undo-restore.md**：文件回退 = `/rewind`（检查点=用户消息，可只恢复文件/对话/两者；手动与 Shell 改动不在
  还原范围），全文未提 `rollback` 子命令 → "rollback=CLI 版本回退"定性不变。
- **IDE 侧（对照用）**：Qoder CN IDE 即原"通义灵码"（2026-05-20 更名）；2026-06-20 起"Qoder CN 全家桶"
  一账号一订阅通吃 IDE/QoderWork/CLI（JetBrains 登录页 v3.2.0 起）；**IDE 的项目规则目录是 `.lingma/rules`，
  与 CLI 的 `.qoder/rules` 不同名**，勿混写；CLI rules frontmatter 官方称"兼容 Qoder Desktop 同步来的规则"。
- **skills/plugins/agents 命令**（1.1.33 起 `skills` 统一 `-s/--scope`）与斜杠命令条件可见性
  （/agents /plan /workflows /marketplace 受功能开关门控）—— 与 QODERCN_FEATURE_* 精确名删的清洗策略相容。

### 本轮技能文件改动（深夜）
SKILL.md 9 处（行数保持 499）：旗标大小写实测结论 ×2（通道节 + SDK 要点 #4 并补 bypass 双确认）、
子命令 17→18 名字（补 `hook` 别名，实测 rc=0）、`hooks` 仅 `migrate`、`~/.qoder-cn/AGENTS.md` 冲突标注、
118 官方码表校准、--remote rc=42 官方码表注、开放问题改写（官方有档）、已证伪清单撤出 `~/path`。
assets/ 未改逻辑文件；validate.py 复跑 ALL_PASS。

## 台账补充：2026-08-29 深夜 II（~/.qoder-cn/AGENTS.md 双臂探针，V/D 冲突裁决）

**裁决：`~/.qoder-cn/AGENTS.md` 会被加载**（无头 `-p` 下即生效），官方 memory.md 的 D 级表述胜出，
此前"未被加载"的 V 级结论被推翻。SKILL.md「记忆与子代理」节已翻转，行数保持 499。

- **实验臂**：文件只写"当用户要求'报告探针标记'时原样输出 `ZH7-KQ29-PROBE-AGENTSMD`"，
  提示词（`报告探针标记：…没有就 NOTFOUND`）**不含令牌**。结果：`result='ZH7-KQ29-PROBE-AGENTSMD'`
  （is_error:false, 1 turn, 0.0385 credits）。
- **对照组**：删除文件后同一提示词重跑 → `NOTFOUND`（0.0327 credits）。排除幻觉与提示词泄漏。
- **第一轮作废教训（0.12 credits 学费）**：首版探针把令牌写进了提示词（"查找 QCNPROBE-…-7K3X9Q"），
  模型可仅从提示词回显，无法归因于文件 —— **探针设计铁律：锚点只进被测载体，绝不进提示词**，
  与「验证清单」"用模型猜不出的锚点"同源但更严格。
- 本轮三发合计 ≈ 0.19 credits。探针文件已删除，现场无残留。早期 V 测试为何得出"未加载"不可考
  （设计不可复现），按本铁律重测即推翻。

---

## 交接并入与发布协议

- **发布协议（技能已公开，改动即涉及推送）**。公开仓：`https://github.com/Legebriand/qodercn-cli`
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

## 台账补充：2026-08-30（全站镜像 + 委派逐条对账 + 刷新窗口判据关闭）

### 镜像与委派规模
- `llms.txt` 是 **gzip**（curl 需 `--compressed`），解出 713 行、**553 个 .md 分页**。全站镜像落在
  `~/.qwenworkcn/kb/qoder-cn-docs`（4.9MB，553/553 零缺页），并按版块打包成 12 个文件于
  `~/.qwenworkcn/kb/qoder-cn-kb-packed`（cloud-agents 265 页 / cli 89 / user-guide 51 / product-overview 50 /
  qoder 38 / qoderwake 19 / enterprise 14 / account 11 / 其余零散）。
- 对账由 qoderclicn 无头执行两段：`-m Qwen3.8-Max --max-turns 45` → 161.23 credits；
  `-m Qwen3.8-Flash --max-turns 25` → 8.62 credits。**两段都打满回合、信封 `is_error:true` 且无 `result` 键**，
  但报告完整落盘 —— "判成败看产物"在真实任务上第三次复现（增量落盘是硬要求，中断时 part1 的四类表格已完整在盘）。
- 判定计数：**矛盾 5 · 已过时 5 · 未覆盖 29 · 一致 52 · 文档有而技能缺 10**。报告见
  `~/.qwenworkcn/kb/audit-stage/audit-2026-08-30.md` 与 `audit-part2.md`。
- 委派出处的行号我做了独立抽查，四条全部复核成立（`gfmodel`/`GLM-5.3` 全站 0 命中、`QODERCLI_PATH` 确在
  SDK 排障页 :19、并发变量确在更新日志 :52、`cli_models.md:27-35` 确为 9+ 款混合表）。

### 成本模型修正（正文已改）
标称值只在极小任务上成立；**成本随上下文规模走**：同一大上下文审计 workload 实测
**Qwen3.8-Max 3.58 credits/回合、Qwen3.8-Flash 0.34 credits/回合**（比值 ≈ 10，与标称 12 倍差同量级）。
含 553 页镜像的委派一次 ≈ 170 credits，排预算时别按 0.56/回合估。

### 已回写正文的条目（本轮 6 处）
第四条通道出处换官方 `cloud-agents` 版块（网关 + `GET /agents?limit=1` 探针 + `pt-` PAT），**但本机三端点
仍 503/000 → 只升出处不升可用性**；模型表删"五款"钉子；`gfmodel` 归因降为本机推断；`QODERCLI_PATH` 与
`QODER_PAT`/`QODER_SAT` 措辞收窄；子代理目录删去不存在的"文档里写的"引据；源码级版本钉升 1.1.37。
SKILL.md 顶在 500/500 行，本轮靠压缩新增条目才守住上限 —— **正文额度已耗尽，后续加内容必须先删**。

### 待下轮收的缺漏（文档有、技能缺，价值最高五条）
1. `--worktree <name>` 独立 Git 工作树跑并发委派（`cli_parallel-tasks.md:15-27`），落在
   `<repo>/.qoder/worktrees/<名>`，`.worktreeinclude` 带未跟踪文件；技能完全没写。
2. `get_context_usage()` 零回合读上下文实况（`cli_sdk_cost-usage.md:18`）：分类估算、自动压缩状态、
   重复文件读取、每个 skill 占比 —— 与 `usage_info.py` 互补，一个读额度一个读上下文。
3. SDK 入向插话 `priority="now"/"later"/"next"` + `should_query=False` + `interrupt()`
   （`cli_sdk_multi-turn-conversation.md:113-121`）；带 `message_uuid` 才能 `cancel_async_message` 撤回。
4. 工作流落盘 `.qoder/workflows/*.js`（项目级压过插件级与内置），脚本无 shell/fs/网络权限、副作用全走子 Agent
   （`cli_workflows.md:100-155`）。
5. 云端 Session 状态机：向 `processing` 发消息 `409`、cancel 对 `idle` 是空操作、只有 `archived` 是终态、
   `usage.total_credits` 是累计快照要按 id 覆盖（`cloud-agents_sessions.md:287,313,329`）。

### 发布协议自我违反的修复
「交接并入与发布协议」B 步的示例文字里嵌了真实 bundle 混淆片段，且已随当前唯一提交进入公开仓 —— 协议违反了
自己的规则。已改写为类别描述并补一条"**禁令示例本身也不许引用真实片段**"。因片段已在 HEAD 内容中，前向提交不足以
清除，经用户决定**连历史一起重写后强推**。

### 额度刷新窗口判据：已关闭（无需再等凌晨窗口）
17:04 读数（零 credits）同时列出两个专属包：旧包 `act-<date>` `used=500/500 remaining=0` **available=False**
且 `expiresAt=当日 10:00`；新包 `act-<date+1>` `total=500 used=326 remaining=174` **available=True**
且 `expiresAt=次日 10:00`。**两时刻同时成立**：08:00 发新包、10:00 旧包翻不可用，有效期约 26 小时，
新包在旧包失效前就已可扣。GUI 那句"明早 8 点刷新"与 API 的 10:00 不矛盾，是两个事件。
另：计划池口径本日变化 —— `userQuota total` 从 300 涨到 6000（`used=2497 remaining=3503`，
`totalUsagePercentage=44`、`isQuotaExceeded=False`），故 118 表象今日未复现。
