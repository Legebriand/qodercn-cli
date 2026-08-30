# ACP protocol notes — verified against `qoderclicn.exe --acp` v1.1.34

Everything below was observed live on Windows (git-bash), driving
`~/.qoder-cn/bin/qoderclicn/qoderclicn.exe --acp` with
`acp_drive.py`. The raw transcripts (full session log, permission-denial log) and the resulting
answer sample were NOT packaged, 2026-08-29.

## 1. Transport

- Line-delimited **JSON-RPC 2.0** over the child's stdin/stdout, one JSON
  object per line, UTF-8, `\n` terminated.
- The agent prints **nothing but JSON-RPC on stdout** (no startup banner).
  Diagnostics/stack traces go to **stderr** (Node-style, not JSON).
- Message direction is determined by shape:
  - `id` + `method` → request (client→agent when we send; agent→client when received)
  - `id` + `result`/`error` → response to a request we sent
  - `method`, no `id` → notification (agent→client)
- NOTE: agent→client request ids start at **0** and count up independently of
  our client→agent ids; colliding numeric ids across directions are normal.

## 2. Environment (Windows + git-bash)

If the host (QwenWork) env is inherited, the CLI aborts with
`sdk_invalid_args` or borrows the host's account. Scrub the denylist in
`acp_drive.py` (mirrors the host's `qcn.sh`): prefixes `QODERWORK_*`, `DWS_*`,
`QODER_AGENT_SDK_*`, `QODER_SDK_*`, `QODER_WORK_*`, `QODER_WORKER_*`,
`QODERCLI_*`, `QODER_SECURITY_*`, plus `QODER_*_THRESHOLD` / `QODERCN_*_THRESHOLD`,
and exact names `QODER_FEATURE_TASKS`, `QODER_FEATURE_WORKFLOWS_DISABLE`,
`QODERCN_FEATURE_TASKS` (feature flags go by exact name, never by a
`QODER_FEATURE_*` family — docs define e.g. `QODERCN_FEATURE_CROSS_SESSION`),
`QODER_CONFIG_DIR`, `QODER_SITE`, `QODER_SCENE`, `QODER_WINDOWS_SHELL_KIND`,
`QODER_ENABLE_AGENT_SESSIONS`, `QODERCN_ENABLE_AGENT_SESSIONS`,
`QODERCN_SERVER_ENDPOINT`, `QODERCN_CLI`, `QODERCN_CONFIG_DIR`.
Keep `QODERCN_PERSONAL_ACCESS_TOKEN` if present (PAT auth).

Then set:
- `QODERCN_CONFIG_DIR` = Windows path of `~/.qoder-cn` (login state `.auth` must exist there)
- `QODER_SITE=cn`
- `QODER_WINDOWS_SHELL_KIND=git-bash` (recommended on Windows)

All path params (`cwd`, `session/new` cwd) must be **native Windows paths**
(`C:\...`), not `/tmp/...` or `/c/...`.

## 3. Handshake

### `initialize` (client → agent, request)
```json
{"protocolVersion": 1, "clientCapabilities": {}}
```
Result (real):
```json
{
  "protocolVersion": 1,
  "authMethods": [{"id": "qoderclicn-login", "name": "Use qoderclicn login", "description": "..."}],
  "agentInfo": {"name": "qoder-cli-cn", "title": "Qoder CLI CN", "version": "1.1.34"},
  "agentCapabilities": {
    "_meta": {"qoder": {"promptQueueing": true}},
    "loadSession": true,
    "sessionCapabilities": {"additionalDirectories": {}, "close": {}, "delete": {}, "fork": {}, "list": {}, "resume": {}},
    "promptCapabilities": {"image": true, "embeddedContext": true},
    "mcpCapabilities": {"http": true, "sse": true}
  }
}
```
- With a valid `~/.qoder-cn/.auth` **no `authenticate` step is needed**; go
  straight to `session/new`.
- Empty `clientCapabilities` is fine: the agent then performs file IO with its
  own tools and never calls `fs/read_text_file` / `terminal/*` on the client.

### `session/new` (client → agent, request)
```json
{"cwd": "C:\\Users\\...\\acp-forge", "mcpServers": []}
```
Result (real, trimmed):
```json
{
  "sessionId": "b6cff76f-...",
  "modes": {"availableModes": [
      {"id": "default", ...}, {"id": "acceptEdits", ...},
      {"id": "bypassPermissions", ...}, {"id": "plan", ...}],
    "currentModeId": "default"},
  "models": {"availableModels": [{"modelId": "auto", ...}, {"modelId": "gfmodel", ...}, ...],
             "currentModelId": "gfmodel"},
  "configOptions": [ ... mode / model / reasoning_effort selects ... ]
}
```
Extra fields beyond the public spec (`modes`, `models`, `configOptions`) are
informational; only `sessionId` is required. Immediately after, the agent
pushes a `session/update` with `sessionUpdate: "available_commands_update"`
listing slash commands.

## 4. Prompting

### `session/prompt` (client → agent, request)

**Public-doc correction:** the content field is **`prompt`, not `content`.**
Sending `content` fails with:
```json
{"code": -32602, "message": "Invalid params",
 "data": {"prompt": {"_errors": ["Invalid input: expected array, received undefined"]}}}
```
Correct params:
```json
{"sessionId": "...", "prompt": [{"type": "text", "text": "..."}]}
```
Result (turn finished):
```json
{"stopReason": "end_turn",
 "userMessageId": "a44b82b8-...",
 "usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
 "_meta": {"quota": {"token_count": {...}, "model_usage": [...]}}}
```
- The **response to `session/prompt` IS the turn-end signal.** There is no
  separate "session ended" notification.
- `stopReason` observed: `end_turn`. Spec values `refusal` / `cancelled`
  apply; treat `refusal` as failure.

### Streaming: `session/update` (agent → client, notification)
```json
{"method": "session/update",
 "params": {"sessionId": "...", "update": {"sessionUpdate": "<kind>", ...}}}
```
Kinds observed:
- `agent_message_chunk` / `agent_thought_chunk` — `update.content` =
  `{"type": "text", "text": "..."}` (thought chunks = reasoning; only message
  chunks are user-visible text).
- `tool_call` — full tool call snapshot: `{toolCallId, status: "pending",
  title, content: [...], kind: "read"|"edit"|"execute", rawInput,
  locations: [{"path": "..."}], _meta: {qoder: {toolName: "Read"}}}`.
  Arrives **before** the matching `session/request_permission`.
- `tool_call_update` — `{toolCallId, status: "completed"|"failed"|...,
  content, rawOutput}`.
- `available_commands_update` — slash-command list (see §3).

## 5. Permissions

### `session/request_permission` (agent → client, **request**, ids 0,1,2...)
Real structure (note: `optionId`s deviate from the public ACP examples):
```json
{"sessionId": "...",
 "options": [
   {"optionId": "proceed_always", "name": "Allow for this session", "kind": "allow_always"},
   {"optionId": "proceed_once",   "name": "Allow",                  "kind": "allow_once"},
   {"optionId": "cancel",         "name": "Reject",                 "kind": "reject_once"}],
 "toolCall": {"toolCallId": "call_...", "status": "pending",
              "title": "Read palette.txt",
              "content": [{"type": "content", "content": {"type": "text", "text": "..."}}],
              "kind": "read",
              "rawInput": {"file_path": "C:\\...\\palette.txt"},
              "_meta": {"qoder": {"toolName": "Read"}}}}
```
Corrections to public docs:
- `optionId`s are `proceed_always` / `proceed_once` / `cancel` — **not**
  `allow_once` / `allow_always` / `reject_once`. The `kind` enum does match
  the spec, so select by `kind`, not by `optionId`.
- File writes arrive as `kind: "edit"` with a diff content block
  `{"type": "diff", "path": "...", "oldText": null, "newText": "...",
  "_meta": {"kind": "add"}}`; `_meta.qoder.toolName` reveals the real tool
  (Write shows as `toolName: "Write"` but permission title "Edit ...").
- Shell commands arrive as `kind: "execute"`.

Client response (verified accepted for both allow and deny paths):
```json
{"outcome": {"outcome": "selected", "optionId": "proceed_always"}}
```
or `{"optionId": "cancel"}` to reject. After the answer the agent proceeds and
later emits the matching `tool_call_update` with `status: "completed"`
(allowed) or a failed/skipped status (denied).

## 6. Session end / interrupt / process lifecycle

- Turn end = `session/prompt` response (§4).
- `session/cancel` (client → agent **notification**, `{"sessionId": "..."}`)
  interrupts a running turn; the pending `session/prompt` response then
  resolves (spec: `stopReason: "cancelled"`).
- **The process does NOT exit on stdin EOF while a session exists**
  (observed alive >10s, even 45s). Without any `session/new` it exits ~0.4s
  after EOF with rc=0.
- `session/cancel` on an *idle* session does **not** terminate the process
  either. Reliable shutdown = close stdin, then `terminate()`/`kill()`
  (what `acp_drive.py` does after a short grace period).
- Extra agent capabilities seen (`sessionCapabilities.close/delete/fork/
  list/resume`, `additionalDirectories`) suggest methods like `session/close`
  exist in this build, but they were not exercised here.

## 7. Failure modes observed

| Symptom | Cause | Fix |
|---|---|---|
| `sdk_invalid_args` on start | host `QODER*/DWS*` env inherited | scrub env (§2) |
| `-32602 Invalid params` on prompt | used `content` field | use `prompt` (§4) |
| Handshake deadlock (host's bash/fifo attempt) | stdout not continuously drained | one dedicated reader thread (§ acp_drive.py) |
| Host pipes held open after run | child inherited host stdout/stderr | explicit `stdin/stdout/stderr=PIPE`, stderr drain thread |
