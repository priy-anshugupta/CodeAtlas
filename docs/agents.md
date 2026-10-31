# Agent integrations

CODEATLAS's core knows nothing about any particular agent. Integrations only install files and
configuration so the agent discovers CODEATLAS at session start and knows how to use it. Each agent
gets what it supports: some have hooks (CODEATLAS can put the answer in front of the model before it
asks), some only an instruction file and MCP.

- [What gets installed](#what-gets-installed)
- [How a session discovers CODEATLAS](#how-a-session-discovers-codeatlas)
- [Claude Code](#claude-code)
- [Codex](#codex)
- [Gemini CLI](#gemini-cli)
- [Cursor](#cursor)
- [Antigravity](#antigravity)
- [Any other agent](#any-other-agent)
- [MCP server](#mcp-server)
- [Skills](#skills)
- [Hooks](#hooks)
- [Consent](#consent)
- [Headless and CI use](#headless-and-ci-use)

## What gets installed

`codeatlas init --agent <name>` (or `auto`, which detects `.claude/`, `.cursor/`, `.codex/`,
`.gemini/` and `.agent/`) installs:

| Agent | Instruction file | MCP | Hooks | Other |
|---|---|---|---|---|
| **Claude Code** | managed block in `CLAUDE.md` | `.mcp.json` | `.claude/settings.json`: SessionStart, UserPromptSubmit, PostToolUse | `.claude/skills/codeatlas-*/SKILL.md` |
| **Codex** | managed block in `AGENTS.md` | `.codex/config.toml` | `.codex/hooks.json`: SessionStart, UserPromptSubmit, PostToolUse | |
| **Gemini CLI** | managed block in `GEMINI.md` | `.gemini/settings.json` | same file: SessionStart, BeforeAgent, AfterTool | |
| **Cursor** | always-on rule `.cursor/rules/codeatlas.mdc` | `.cursor/mcp.json` | `.cursor/hooks.json`: sessionStart, afterFileEdit | on-request rules for audit, refresh, decisions |
| **Antigravity** (experimental) | managed block in `AGENTS.md` | user-level, added by `agy mcp add` when you agree | `.agents/hooks.json`: PreInvocation, Stop | `.agents/skills/codeatlas-context/` |
| **Generic** | managed block in `AGENTS.md` | | | |
| **Git hooks** (any agent, optional) | | | `post-commit`, `post-merge`, `post-checkout` run `codeatlas update --quiet` | |

Every installer merges into existing files instead of replacing them, backs up what it modifies
to `.aicontext/cache/backups/`, marks what it owns as `codeatlas-managed`, is idempotent, and is
fully reversed by `codeatlas uninstall-integration`. A user's own hooks, MCP servers and TOML tables
are never touched; a `[mcp_servers.codeatlas]` table you wrote yourself is left alone.

## How a session discovers CODEATLAS

An agent only knows what is in its context, so CODEATLAS places itself there through several
layers. If one is missing, another still works.

```mermaid
flowchart TB
    S((New agent session)) --> L1["1 Instruction block<br/>CLAUDE.md / AGENTS.md / GEMINI.md / rules"]
    S --> L2["2 Session-start hook<br/>compact brief + freshness"]
    S --> L3["3 Prompt hook<br/>the code the request needs, before the first turn"]
    S --> L4["4 MCP tools<br/>codeatlas_task in the tool list"]
    S --> L5["5 Plain files<br/>.aicontext/AGENTS.md readable anyway"]
    L1 & L2 & L3 & L4 & L5 --> W["Agent edits from what it was given<br/>or asks codeatlas task once"]
```

| Situation | What the agent sees |
|---|---|
| Enabled for you, CODEATLAS installed | The compact brief; the code for each request added to the prompt (agents with a prompt hook) or one `codeatlas task` call away |
| Initialized by a teammate, not enabled for you | One line saying CODEATLAS is available and how to enable it; nothing runs |
| `.aicontext/` committed, CODEATLAS not installed | Hooks are silent; the instruction block still points to `.aicontext/AGENTS.md` |
| Never initialized | Nothing |
| Enabled but paused | Hooks do nothing; `codeatlas status` shows `paused` |
| Edits made without any hook | The next answer checks the working tree and updates the changed files first |

## Claude Code

Hooks added to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup|resume|clear|compact",
        "hooks": [{ "type": "command", "command": "codeatlas hook session-start", "timeout": 10 }] }
    ],
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "codeatlas hook user-prompt", "timeout": 10 }] }
    ],
    "PostToolUse": [
      { "matcher": "Edit|Write|MultiEdit",
        "hooks": [{ "type": "command", "command": "codeatlas hook post-edit", "timeout": 5 }] }
    ]
  }
}
```

Plain stdout from `SessionStart` and `UserPromptSubmit` hooks is added to the conversation.
MCP entry in `.mcp.json`: `{ "mcpServers": { "codeatlas": { "command": "codeatlas", "args": ["mcp"], "alwaysLoad": true } } }`.
`alwaysLoad` keeps `codeatlas_task` listed from the first turn: without it Claude Code hides MCP tools
behind its tool search, and every first lookup costs an extra model call that re-sends the whole
context (measured at 0.6–0.8 extra calls per session).
The managed `CLAUDE.md` block (about 100 tokens) tells the agent to start with `codeatlas task`, and
never to run `codeatlas init`, `scan`, `enable` or `install --global` unless you ask.

## Codex

`.codex/config.toml` gets a managed block:

```toml
# codeatlas-managed:start
[mcp_servers.codeatlas]
command = "codeatlas"
args = ["mcp"]
startup_timeout_sec = 20
tool_timeout_sec = 60
# codeatlas-managed:end
```

and `.codex/hooks.json` the same three events as Claude Code, with `PostToolUse` matching
`apply_patch|Edit|Write` (CODEATLAS reads the changed files from the patch). Codex loads project
`.codex/` settings only for a **trusted project** and asks you to review new hooks (`/hooks`);
`codeatlas init` reminds you. Codex sets aside hook output beyond about 2,500 tokens, so the prompt
hook's default budget (1,200) stays well under it.

## Gemini CLI

`.gemini/settings.json` gets the MCP server and three hooks (timeouts in milliseconds):
`SessionStart` and `BeforeAgent` run with `--format json`, which prints
`{"hookSpecificOutput": {"additionalContext": ...}}`, and `AfterTool` (`write_file|replace`)
updates the index. Instructions go in a managed block in `GEMINI.md`, which Gemini CLI reads by
default.

## Cursor

An always-on rule, `.cursor/rules/codeatlas.mdc`, holds only the short instruction block (it is sent
every turn). The audit, refresh and decision procedures are separate rules the agent asks for by
description, so they cost nothing in a session that never audits. `.cursor/hooks.json` adds
`sessionStart` (the brief, returned as `additional_context`) and `afterFileEdit` (index update).
Cursor's `beforeSubmitPrompt` can only block a prompt, not add to it, so there is no prompt hook:
the agent calls `codeatlas_task` (or `codeatlas task`) itself.

## Antigravity

Experimental. A rule under `.agents/rules/` is only loaded unconditionally when it declares
`trigger: always_on`, so the instruction block goes into `AGENTS.md`, which Antigravity always
reads (an older `.agent/rules/codeatlas.md` written by CODEATLAS is removed). The `codeatlas-context` skill
goes in `.agents/skills/`. `.agents/hooks.json` gets two hooks:

- `PreInvocation` (`codeatlas hook pre-invocation`) runs before every model call. It reads the newest
  request from the transcript and injects the packet once per request as a `userMessage` (an
  `ephemeralMessage` would be dropped after the first model call), so the agent does not have to
  remember to ask.
- `Stop` (`codeatlas hook stop`): the finish-time check below.

MCP servers are configured in a user-level file (`~/.gemini/config/mcp_config.json`), which CODEATLAS
never edits on its own. When `agy` is installed, `codeatlas init` asks whether to add it for you with
`agy mcp add codeatlas codeatlas mcp` (never under `--yes`), and `codeatlas uninstall-integration` offers to
remove that entry again; otherwise it prints the entry to add. Without it the agent still gets
the packet from the hook, but cannot call `codeatlas_task` for follow-up lookups.

## Any other agent

Agents that read a root `AGENTS.md` get the same managed block describing the workflow as CLI
commands. Configure the MCP server manually if your agent supports MCP.

## MCP server

`codeatlas mcp` runs a local stdio server started by the agent. There is no network listener. Each
tool is a thin wrapper over the same library function as the corresponding CLI command, returns
structured JSON, and reports problems as structured errors (`not_enabled`, `index_missing`,
`ambiguous_target` with candidates, `not_found` with suggestions) so the agent can recover.

Most agents send every tool's schema to the model on every turn, so the default **lean** profile
exposes only what a coding task needs. `codeatlas mcp --profile full` (or `CODEATLAS_MCP_PROFILE=full`)
adds the rest.

Every answer is sent once, as compact JSON (or the packet text for `codeatlas_task`), never as
indented text plus a second `structuredContent` copy that a host may forward too. Each tool
carries MCP annotations: lookups are `readOnlyHint`, so a host can run them without asking, and
the few tools that write (only inside `.aicontext/`) say so; none is destructive or reaches the
network. The compact brief is also a resource, `codeatlas://brief`, which costs nothing until a host
reads it. `codeatlas_task` also declares `_meta["anthropic/alwaysLoad"]`, so a host that defers MCP tools still lists
it upfront, and the server instructions say when to call it: for code the agent does not have yet,
never again for code a hook already delivered.

The default install is the prompt hook together with MCP: the hook puts the first answer in the
request, and `codeatlas_task` serves every follow-up within the same session, so code already sent is
referenced, not repeated.

| Tool | Profile | Input | Returns |
|---|---|---|---|
| `codeatlas_status` | lean | | Enable state, freshness, changed files, drift, stale sections, audit summary |
| `codeatlas_task` | lean | `query`, `budget?`, `repeat?` | The code, every exact string match, callers, tests and impact for a request in one call |
| `codeatlas_context` | lean | `target`, `budget?`, `depth?`, `with_source?` | A context pack |
| `codeatlas_impact` | lean | `target`, `depth?` | Dependents by distance and tests to run |
| `codeatlas_brief` | full | `full?` | The compact brief (or all of `AGENTS.md`) plus the freshness line |
| `codeatlas_search` | full | `query`, `limit?`, `semantic?` | Ranked hits (id, kind, file, lines, score, snippet) |
| `codeatlas_locate` | full | `name` | Candidates with file and lines |
| `codeatlas_module` | full | `name` | A module summary |
| `codeatlas_refresh_prepare` | full | `sections?` | Refresh packet per stale section |
| `codeatlas_refresh_commit` | full | `section`, `text` | Validation result; resets drift on success |
| `codeatlas_audit_plan` | full | `scope?`, `since?`, `depth?` | The audit plan |
| `codeatlas_audit_record` | full | `finding` | Assigned id, or duplicate / reopened, or validation errors |
| `codeatlas_audit_update` | full | `id`, `status` | The updated finding |
| `codeatlas_audit_report` | full | | Report path and new / fixed / persisting counts |
| `codeatlas_decisions` | full | | Recorded architecture decisions |
| `codeatlas_decision_record` | full | title, context, decision, … | The recorded decision |
| `codeatlas_graph_view_url` | full | `focus?`, `depth?` | The local viewer URL, if you have `codeatlas view` running |

`codeatlas_task` remembers the code it returned during the server's life and answers a repeat with
one-line references; pass `repeat=true` after the agent's context was compacted. Only
`codeatlas_refresh_commit`, `codeatlas_audit_record`, `codeatlas_audit_update`, `codeatlas_decision_record` and
`codeatlas_audit_report` write, and only inside `.aicontext/`. No tool edits source code or runs
shell commands. If CODEATLAS is not enabled for the current user, or is paused, the server exposes
only `codeatlas_status`, which reports that state.

## Skills

Skills are the instruction files through which your agent does CODEATLAS's thinking. They are
product code: versioned, snapshot-tested, and checked so they only mention commands, flags and
fields that exist.

| Skill | Triggers | Procedure |
|---|---|---|
| `codeatlas-context` | Start of any coding task; "where is / what calls / what breaks if" | `codeatlas task` → edit from the answer → follow up with `context` / `impact` → run the listed tests |
| `codeatlas-refresh` | You ask to refresh the brief, or sections you wrote are reported stale | refresh prepare → read the packet → rewrite each stale section within its budget → refresh commit |
| `codeatlas-audit` | "Audit", "find bugs", "what's broken", "check before I merge" | See [audit.md](audit.md) |
| `codeatlas-decisions` | You make or ask to record a design decision, or the agent needs to know why code is built a certain way | decision list or search → decision show → decision add (only for decisions you made) |

Shared guardrails: never run `init`, `scan`, `enable` or `install --global` unasked; never load
whole JSON artifacts; fall back to a targeted grep (never a full scan) when static analysis
misses dynamic calls; never hand-edit `.aicontext/`. `codeatlas-context` is deliberately short: its
text is loaded whenever it triggers.

## Hooks

Hooks must never break or slow an agent session. They start without importing the full command
line (about 0.2 s), always speak UTF-8 (a Windows pipe defaults to a code page that would make
a non-Latin character silently drop the output), always exit 0, print nothing on error (errors go
to `.aicontext/cache/hook.log`), and do nothing if CODEATLAS is missing, not enabled for you, or paused.

- **session-start**: consent check, a bounded catch-up for changes made outside the agent, then
  prints the compact brief and a freshness line.
- **user-prompt**: looks up the user's own words and adds the answer to the prompt. It says
  nothing for greetings, confirmations, slash commands and shell escapes, nor when the match is
  weak (so an unrelated request costs zero tokens), adds at most `prompt_budget` tokens (default
  2,000). It starts at 1,200 and expands only if that supplies complete edit evidence.
  It sends code only once per session: repeats are one-line references. If the query
  caches are cold (a fresh clone) it starts building them in the background and stays silent
  once. Switch it off with `prompt_context = false` in the config or `CODEATLAS_PROMPT_CONTEXT=0`.
- **post-edit**: if the edited file is a source file in an enabled repository, starts
  `codeatlas update` for it in a detached process and returns immediately. A question asked before it
  finishes waits for the same lock and then sees the edit.

## Finish-time check and read dedupe

- **Stop hook** (`codeatlas hook stop`; Claude Code, Codex, Antigravity): for a request that changes a
  value everywhere it appears, the prompt hook notes that its answer was an exhaustive list. When
  the agent is about to finish, the hook re-runs the request in verify mode; if the old number or quantity
  is still in the code, it sends the agent back **once** with the remaining lines, otherwise it says
  nothing and costs nothing. It never loops (`stop_hook_active` is honoured) and protects the result
  rather than shortening the session. Verified against Codex 0.162 and documented for Claude Code.
- **Shortened command output** (`codeatlas hook shorten-output`; Claude Code `PostToolUse` on `Bash`;
  install with `codeatlas init --shorten-output`, off by default): long test, build and git output is
  replaced, through `updatedToolOutput` in Bash's own output shape, by what `codeatlas filter` keeps.
  Failure lines and their context are never dropped, the full output is saved and its path shown
  last, and output the filter cannot shorten by at least 20 lines is left alone.
  `CODEATLAS_SHORTEN_OUTPUT=0` switches it off.
- **Read dedupe** (`codeatlas hook dedupe-read`; Claude Code `PreToolUse` on `Read`; install with
  `codeatlas init --dedupe-reads`, off by default): refuses a re-read of an unchanged range the agent
  already has, with a reason saying so. It only ever **denies**; it never approves a call, so it cannot widen
  what the agent may do. Entries expire after 20 minutes (a compaction may have dropped the text), an edited
  file is always readable, and `CODEATLAS_DEDUPE=0` switches it off. A matching `PostToolUse`
  hook records only text actually returned by a successful read; failed or denied reads never
  block a retry. `SessionStart` clears coverage on startup, resume, clear and compaction.
  Unknown response formats remain readable. Reinstall the integration to add these companion hooks.
- **Skills**: only `codeatlas-context` is installed by default, because every skill's name and description sit
  in the agent's context on every call. `codeatlas init --all-skills` adds audit, refresh and decisions.

## Settings that belong to the host

CODEATLAS cannot change these, but they matter for cost:

- **Claude Code**: route exploration to a cheaper model (`CLAUDE_CODE_SUBAGENT_MODEL=haiku`, or a
  `model:` in a subagent file). Delegation overhead can outweigh the saving on small tasks.
- **Codex**: `model_reasoning_effort` and `model_verbosity` are cost levers; a compaction replaces the cached prefix
  and each retry re-sends the whole context; AGENTS.md stops being read at 32 KiB (`project_doc_max_bytes`).
  MCP tools are loaded on demand, so an agent only finds `codeatlas_task` if it searches for it: the prompt hook is the
  reliable delivery there.
- **Gemini CLI**: prompt caching applies with API-key authentication, and short prompts under the model's minimum
  (4,096 tokens on newer Flash models) do not qualify.

## Consent

CODEATLAS runs in a repository only after a user enables it there, and each user decides for
themselves:

- `codeatlas init` enables CODEATLAS for the user who ran it. Teammates run `codeatlas enable`.
- The flag lives in `~/.config/codeatlas/repos.toml` (or `$CODEATLAS_CONFIG_HOME/repos.toml`), keyed by
  repository path and the repository id in `manifest.json`. It is never committed.
- Without the flag, `codeatlas hook session-start` prints at most one line and does nothing else;
  `codeatlas hook user-prompt` and `post-edit` exit silently; the MCP server exposes only
  `codeatlas_status`; queries read the committed index but never update it.
- `codeatlas pause` / `codeatlas resume` turn automatic activity off and on without removing anything.

Agents must never run `codeatlas init`, `codeatlas scan`, `codeatlas enable` or `codeatlas install --global`
unless you explicitly ask in the current conversation. Every shipped skill and instruction block
says so.

## Headless and CI use

CODEATLAS has no API client. To run CODEATLAS-driven work in CI, run your agent in headless mode, for
example:

```bash
claude -p "run the codeatlas-audit skill with depth quick and summarize the report"
```
