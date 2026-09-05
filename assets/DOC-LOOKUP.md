# 官方文档查证入口（映射表）

`https://docs.qoder.cn/llms.txt` 是官方给 agent 的**全站点索引**（约 430 行，可整读）。
任意页面把 URL 加上 `.md` 就能拿到干净 markdown；`.md` 页首还会主动提示"先取 llms.txt
发现页面"，这就是设计好的工作流。

- **`llms-full.txt` 是子集（约 3.6MB），绝不可整读**：参考类页面（settings-reference、
  permissions、mcp-reference）**不在其中**，拿它做全量核对必然假阴性 —— 必须逐页取 `<url>.md`。
- 更新日志 `product-overview/qoder-cn-cli.md` 把约 90 个版本塞在**同一页**，整读会让后续回合
  耗时暴涨；只取需要的版本区间。
- SKILL.md 正文是**缓存**，会过期；下表与本正文冲突时以文档为准。

| 要查的东西 | 页面（前缀 `https://docs.qoder.cn/`） |
|---|---|
| 旗标默认值与子命令 / 环境变量全表与路径 / 权限规则 | `cli/cli-reference.md`、`cli/settings-reference.md`、`cli/permissions.md` |
| MCP（含已确认的 `mcp add <name> -- <cmd>`、`list`、`remove`）/ headless 契约 / ACP（仅文档索引，非本技能采纳的委派通道） | `cli/mcp-reference.md`、`cli/run-in-scripts.md`、`cli/acp.md` |
| 模型与推理强度 / 记忆文件位置 / 回退与恢复 | `cli/models.md`、`cli/memory.md`、`cli/how-memory-works.md`、`cli/undo-restore.md` |
| 安装与升级（`install.sh`/`ps1`/`cmd`、npm `@qodercn-ai/qoderclicn` Node≥20、Windows arm64 不支持；`general.enableAutoUpdate` **默认开**，长委派建议显式关） | `cli/installation.md` |
| SDK 认证·权限·检查点·错误码·Python 参考 / 内置 Subagent 与 Skills | `cli/sdk/{authentication,permissions,checkpoint,errors,references-python}.md`、`cli/builtins-reference.md` |
| 用量与额度（`/usage` 只有交互模式有） | `cli/usage.md` |
| 按报错原文定位 | `cli/troubleshoot-faq.md` 及 `cli/troubleshoot-*.md` |
