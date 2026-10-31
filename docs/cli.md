# CLI reference

Every command accepts `--root PATH` (default: the repository containing the current directory)
and `--help`. Commands with structured output accept `--json`. Human output is compact Markdown;
hook commands are silent.

For normal CLI commands, `--root` can also appear before the command. Task retrieval
accepts `--session` there too: `codeatlas --root PATH --session ID task "request"`.
Command-level options override these defaults. Session defaults apply to task retrieval;
host hooks use the repository and session supplied by their host event.

- [Setup and consent](#setup-and-consent)
- [Index](#index)
- [Navigation](#navigation)
- [Narrative and decisions](#narrative-and-decisions)
- [Audit](#audit)
- [Graph](#graph)
- [Agent plumbing](#agent-plumbing)
- [Exit codes](#exit-codes)

## Setup and consent

### `codeatlas init`

Enable CODEATLAS in this repository. Shows every change first and asks before making it.

| Option | Default | Description |
|---|---|---|
| `--agent` | `auto` | `claude-code`, `cursor`, `codex`, `gemini`, `antigravity`, `generic`, `auto` or `none` |
| `--hooks / --no-hooks` | ask | Install agent hooks (brief at session start, the code a request needs added to the prompt, update after edits) |
| `--mcp / --no-mcp` | ask (yes) | Register the MCP server; hook + MCP is the default install |
| `--git-hooks / --no-git-hooks` | ask | Install git `post-commit`, `post-merge`, `post-checkout` hooks |
| `--scan / --no-scan` | ask | Run the initial scan |
| `--shorten-output` | off | Claude Code: shorten long command output before it is read (failures kept) |
| `--dedupe-reads` | off | Claude Code: refuse to re-read an unchanged file already in context |
| `--yes`, `-y` | | Skip prompts (for scripts); never changes user-level agent settings |

Running `init` twice changes nothing. Existing config files are merged, never overwritten, and
backed up to `.aicontext/cache/backups/` before modification.

### `codeatlas enable` · `codeatlas disable`

Turn CODEATLAS on or off for **you** in this repository. The flag is local
(`~/.config/codeatlas/repos.toml`) and never committed; nothing in the repository changes.

### `codeatlas pause` · `codeatlas resume`

Stop and restart all automatic activity (hooks become no-ops) without removing anything.

### `codeatlas uninstall-integration [--purge]`

Remove every CODEATLAS-managed block, hook, MCP entry and skill, restoring backups. `--purge` also
deletes `.aicontext/` and your consent flag, after confirmation.

### `codeatlas install --global [--suggest]` · `codeatlas uninstall --global`

Add (or remove) a short note in your agent's user-level instructions, for example
`~/.claude/CLAUDE.md`: use CODEATLAS where it is enabled and never run `init` or `scan` unasked.
`--suggest` additionally lets agents mention CODEATLAS once in large repositories without an index.
Never run implicitly.

### `codeatlas doctor`

Diagnose the setup: Python and CODEATLAS versions, `codeatlas` on `PATH`, index and schema versions,
consent, freshness, artifact integrity, MCP SDK, git, parsers and the viewer bundle.

```text
 ✓ python           3.14.4 (win32)
 ✓ codeatlas            0.1.0
 ✓ initialized      /home/you/repo/.aicontext
 ✓ consent          enabled
 ✓ freshness        index fresh
 ✓ artifacts        match the manifest
 ! git              no git history (churn/co-change disabled)
 ✓ languages        javascript, python (counted, not parsed: shell)
 ✓ viewer bundle    present
```

### `codeatlas doctor --session ID|latest`

Was CODEATLAS used in one agent session, and if not, why not: whether the prompt hook fired (and why
it stayed silent), how many `codeatlas task` / `codeatlas_task` calls the agent made, which hook config
files exist, and a one-line verdict. Reads the local work log, so it works for sessions in which
the hooks ran. The session line names the agent (`claude-code`, `codex`, `antigravity`, `gemini`,
`cursor`) recognised from the hook payload, so runs on different agents are not mixed up when
comparing them.

### `codeatlas filter -- <command>`

Run a command and print only what matters of its output: pytest, jest/vitest/mocha, flutter, go,
cargo, npm/yarn installs and builds, and git. Failure lines (and 3 lines around each) are never
dropped; output under 60 lines is unchanged; `git diff`/`log` are never cut in the middle. The
full output is saved under `.aicontext/cache/tee/` and its path is printed last; the exit status
is the command's own. Active only where CODEATLAS is enabled for you, otherwise it just runs the
command. See `docs/adr/0004-output-filtering.md`.

## Index

### `codeatlas scan [--full] [--json]`

Build the full index into `.aicontext/`. Unchanged files reuse cached hashes and parses unless
`--full` is given.

### `codeatlas update [FILE ...] [--files FILE ...] [--quiet] [--json]`

Incremental update: re-parse only changed, added or deleted files. Files known to have changed
may be named as arguments, after `--files`, or with several `--files`; `codeatlas update a.py b.py`,
`codeatlas update --files a.py b.py` and `codeatlas update --files a.py --files b.py` all work. Named
files are always re-hashed. Exits early without writing when nothing changed.

Updates take a lock (`.aicontext/cache/update.lock`), so a hook, a query and a manual update
never write the index at the same time. You rarely need this command: every query checks the
working tree first and brings changed files up to date itself.

### `codeatlas status [--json]`

Consent state, index freshness, drift, stale brief sections and an audit summary.

```text
enabled · index fresh
last update 2026-09-27T15:26:54Z · 23 files · 33 symbols · 3 test files
```

The state line is one of `not initialized`, `initialized · not enabled for you`, `enabled` or
`paused`.

### `codeatlas watch [--interval SECONDS]`

Keep the index fresh while you work, for editors and agents without hooks. Default interval
1.0 s (minimum 0.2). Ctrl+C stops.

### `codeatlas migrate`

Upgrade `.aicontext/` to the installed CODEATLAS version's schema and rebuild the index.

## Navigation

### `codeatlas knowledge [--budget N] [--json]`

Inspect the persistent local project inventory: file/symbol counts, call/import relationships,
languages and top modules. Default budget 600 estimated tokens. This is an on-demand inspection,
not an extra orientation step before editing. Use `codeatlas task` for the requested change.
`codeatlas_knowledge` is available in the full MCP profile.

### `codeatlas task "<request>" [--mode auto|overview|code|verify] [--detail full|brief] [--budget N] [--session ID] [--json]`

Start a coding task with one local call. Pass the request in the user's own words, a symbol
name, or a file path. `auto` selects a signature/relationship map for architecture requests
and source for edits. `--mode overview` explicitly requests a compact map (a file path gives
its symbol outline); `--mode code` explicitly requests source. MCP `codeatlas_task` accepts the
same `mode`. Maps are selective and never claim to contain enough source to edit.

Examples: `codeatlas task "repository architecture"`, `codeatlas task src/service.py --mode overview`,
`codeatlas task "fix the cache expiry" --mode code`. Exact source follow-ups support
`src/service.py::Class.method`, `src/service.py:42` (enclosing symbol) and
`src/service.py:42-65` (only that range). The source answer contains:

- **Literals**: every exact occurrence of the strings, names and quantities the request
  mentions, with `file:line` and the line. Quoted strings (`'Something went wrong'`), code names
  (`LIFETIME_MINUTES`, `EmailCode.verify`), numbers with units ("10 minutes", found even as
  `LIFETIME_MINUTES = 10`) and multi-word phrases are searched across the whole indexed source
  through the postings, without scanning the repository. A list marked *exhaustive* covers every
  matching line, so the agent need not grep those strings again. Capped scans and unavailable
  candidate files are explicitly marked limited; their totals are lower bounds. New names are
  reported only after a complete candidate search.
- **Blocks**: the code that best matches the request, with line numbers: a whole function when
  it is small, windows around the matching lines otherwise. Whole files and module headers are
  never returned as an orientation strategy. Cooperating methods in an affordable small class
  can be returned together. Used Python constants/imports/local helpers are included when they
  fit; unrelated file headers are excluded. Body and symbol rankings use reciprocal-rank fusion.
- **Callers** of the symbols the answer is about, with the calling line, plus **tests** that
  mention them and the **impact** (how many symbols and files depend on them).
- **Confidence** (`high`, `medium`, `low`), `sufficient`, and a `Next:` line saying how far to
  trust the answer. `low` says to search narrowly. Partial packets list precise `read_next`
  ranges rather than requiring a repeat of the whole file. Completeness is about the supplied
  evidence, not a guarantee that an edit is correct or static graphs cover dynamic dispatch.

The default budget is 2000 (range 128-32000), using `ceil(characters/4)` across the entire
returned packet, including serialization and metadata. It is an estimate, not the model's token
count; host and tool envelopes are outside it.

Before answering it checks the working tree and brings any changed files up to date (only for a
user CODEATLAS is enabled for), so an edit made without running `codeatlas update` is still seen.
Source is returned only if it matches the indexed hash.

`--session ID` (or `CODEATLAS_SESSION`) remembers which code ranges this session already received;
repeats come back as one-line references instead of the code again. The MCP server does this
for its own lifetime (`repeat=true` forces the full answer). MCP also accepts `session="ID"`
or `CODEATLAS_SESSION`, sharing the hash-invalidated range memory with CLI and prompt hooks. Use
the same host-session ID across those surfaces; a new conversation must use a new ID.

MCP `codeatlas_task` now defaults to `format="compact"`: the same bounded text that CLI renders.
Consumers expecting the structured packet must request `format="json"`. Errors remain
structured and set the MCP error flag. Other MCP operations retain their existing format.

The query caches (`.aicontext/cache/index-*.sqlite`, `source-v2.sqlite`) are built by `codeatlas scan`
and bounded task packets in `cache/tasks/` are local and disposable. Task packets are keyed by
query, mode, budget, source hashes/stat revisions and artifact versions. Requests with session
memory are assembled against that session rather than returning a cached full packet. No model API, embeddings download or
API key is involved.

Targets for the follow-up commands can be a symbol id (`shop.pricing.discounts.apply_discount`),
a file path, `file:line`, a module, or a route (`"GET /orders"`). An ambiguous target returns
ranked candidates instead of guessing.

Further lines a packet can carry (edit requests; each only when it fits the budget):

- **Patch**: for an explicit old → new change ("from 23 to 25", "rename a to b") at sites the
  exact-match search listed exhaustively, a unified diff written under
  `.aicontext/cache/patches/` and checked with `git apply --check`. The packet prints the one
  command that applies it: `git -c core.autocrlf=false apply <path>` (byte-exact, so Windows line-ending
  conversion cannot rewrite whole files). CODEATLAS only writes the patch text into its own cache; it never edits
  a source file. Nothing is offered when the old value has no complete list, a new name already
  exists, or a listed line no longer matches the index.
- **Twins**: the same function (same name and signature, bodies at least 65–80% alike) defined in
  more than one file; the change usually belongs in all of them. Generic names (`get`, `run`) and
  names defined in more than six places are ignored.
- **Large files, read only**: `offset`/`limit` windows around the listed sites in files over 600
  lines, so a 1,700-line locale file is not read whole.
- **Batch** and **Done when**: the listed files are independent (read and edit them together in one turn),
  and the condition that ends the task.
- Archived or vendored code (`archive/`, `legacy/`, `vendor/`) and the other area of a monorepo
  than the request names (frontend when it says backend) rank lower. Related tests fall back to the
  nearest test file when nothing links to the code.

`--detail brief` (MCP `detail="brief"`) returns sites and tests only, at most 800 tokens.
`--mode verify` re-asks the request after editing and lists only the sites that still match the
old value (numbers and quantities); it never uses the packet cache.

### `codeatlas find PATTERN... [--regex] [-i] [--glob G] [--budget N] [--json]`

Up to eight searches in one call, over the indexed code and the text/data files (translations,
config, docs). Substring by default (`--regex` for expressions), grouped by file with the exact
lines, application code before tests, archives and migrations, and cut to `--budget` (default
1,500 tokens) with a count of what was left out. One call replaces several greps, each of which
would carry the whole conversation again. MCP: `codeatlas_find` (standard and full profiles).

### `codeatlas diff "<request>" [--show] [--json]`

Write the checked patch for a request without the rest of the packet and print the command that
applies it (see **Patch** above). Prints why when there is nothing safe to offer.

### `codeatlas note "<text>" [--session ID]`

Leave a one-line handoff for the next session: what changed, what is left, what to watch for
(at most 600 characters). Stored in the local work log; see [configuration](configuration.md#work-log).

### `codeatlas recall [QUERY] [--limit N] [--json]`

Earlier sessions from the work log, most recent first, or those whose requests, notes, files
or symbols match `QUERY`: what was asked, which files and functions were edited, and notes.

### `codeatlas brief [--full]`

Print the compact session brief and a one-line freshness status. This is what the session-start
hook injects: the project's languages and run/test/lint commands, any narrative a human or agent
has written, and the one-line way to use CODEATLAS. Generated overviews, placeholders and module
rankings are left out (a repository overview does not help an agent find files faster and costs
tokens every turn). `--full` prints the whole `.aicontext/AGENTS.md`.

### `codeatlas search QUERY [--limit N] [--semantic] [--json]`

Ranked free-text search over names, qualified ids, docstrings, paths and routes (BM25, local).
`--limit` 1–100, default 10. `--semantic` blends in a local embedding model and needs
`codeatlas-ctx[semantic]` (see [semantic retrieval](configuration.md#semantic-retrieval)).

### `codeatlas locate NAME [--limit N] [--json]`

Resolve a name to candidates with `file:lines`: exact match, then qualified suffix, then fuzzy.

### `codeatlas context TARGET [--budget N] [--depth 1|2] [--with-source] [--json]`

Build a context pack: location and signature, summary, risk, open findings, and a read list of
callers, callees, tests and related code that fits the budget (default 2,000 tokens, minimum
100). `--with-source` inlines the target's body when it fits.

### `codeatlas impact TARGET [--depth 1-6] [--json]`

Blast radius: dependents grouped by distance (default depth 3) and the tests to run.

```text
# Impact: `shop.pricing.discounts.apply_discount`
8 dependent symbols across 5 files

## Distance 1
- `shop.checkout.cart.Cart.total`
- files: src/shop/checkout/cart.py
…
## Tests to run
- tests/test_cart.py
- tests/test_discounts.py
- tests/test_orders.py
```

### `codeatlas module NAME [--json]`

Show a module summary from `.aicontext/modules/`.

### `codeatlas trace SOURCE TARGET [--depth 1-8] [--max-nodes 2-1024] [--json]`

Find a shortest directed static path between two symbols (calls) or two modules
(imports). Defaults: depth 4, at most 128 visited nodes. Each edge reports its
confidence, resolution and extracted/inferred provenance. Source revisions are
verified; stale files or exhausted traversal limits mark the search partial.
An absent path in a partial search does not prove disconnection. Static paths
do not establish runtime execution. The full MCP profile exposes `codeatlas_trace`.

## Narrative and decisions

### `codeatlas refresh prepare [--sections NAME ...]`

Emit what the agent needs to rewrite each stale section of `AGENTS.md` or a module summary:
relevant context, the structural diff since the last refresh, and a token budget per section.

### `codeatlas refresh commit SECTION --file FILE [--json]`

Validate and write one section (`purpose`, `architecture`, `conventions` or `modules/<name>`),
resetting its drift. Generated regions can never be overwritten this way.

### `codeatlas decision add | list | show`

Record, list and print architecture decisions in `.aicontext/decisions/`.

### `codeatlas decision search QUERY [--limit 1-50] [--json]`

Search compact decision records, default limit 10. Results include IDs, titles,
status and source-evidence validity (`current`, `stale`, or `unverified`), without
the full rationale. Superseded and deprecated records are excluded from search.
Expand a selected record with `codeatlas decision show ID`. MCP supports
`codeatlas_decisions(query=...)` and `codeatlas_decisions(expand_id=ID)`; expanded results
also report evidence validity. Old records without recorded source hashes are
unverified rather than assumed current.

## Audit

See [audit.md](audit.md) for the full workflow.

| Command | Purpose |
|---|---|
| `codeatlas audit plan [--scope all\|changed\|PATH] [--since REF] [--depth quick\|standard\|deep] [--json]` | Write `audit/audit_plan.json`: toolchain commands, prioritized targets, smells, dead-code candidates, prior findings to re-verify |
| `codeatlas audit record --json FILE\|-` | Validate and store a finding; assigns `F-###` ids and dedupes |
| `codeatlas audit update ID --status open\|fixed\|wontfix\|false_positive [--note TEXT] [--json]` | Change a finding's status |
| `codeatlas audit report [--json]` | Render `audit/REPORT.md` with a diff against the previous audit |

## Graph

### `codeatlas view [--focus TARGET] [--depth 1-4] [--port N] [--no-open]`

Start the local graph viewer on `127.0.0.1` (random free port by default, one-time token in the
URL) and open it in your browser. `--focus` opens the local graph around a target. See
[viewer.md](viewer.md).

### `codeatlas graph export`

| Option | Description |
|---|---|
| `--html FILE` | Self-contained HTML viewer (works offline, no server) |
| `--obsidian DIR` | Obsidian vault: one note per module or file with `[[wikilinks]]` and tags |
| `--mermaid` · `--dot` · `--graphml` · `--json` | Text formats, to stdout or `--out FILE` |
| `--around TARGET` · `--depth 1-4` | Only the neighbourhood of a target |
| `--level package\|file\|symbol` | Level of detail (default `file`) |
| `--layer import\|call\|tests\|cochange` | Which relationships (default `import`) |
| `--symbols` | HTML and Obsidian: include symbol-level nodes |
| `--with-graph-colors` | Obsidian: add risk colour groups to the graph view |

Mermaid and DOT exports without `--around` are capped at 150 nodes to stay readable.

## Agent plumbing

| Command | Used by |
|---|---|
| `codeatlas mcp [--profile lean\|standard\|full]` | The agent, from `.mcp.json`: runs the MCP server over stdio. `lean` (default) exposes only `codeatlas_task` (its schema is re-sent on every model call, so it stays tiny); `standard` adds `codeatlas_status`, `codeatlas_context`, `codeatlas_impact`; `full` adds search, locate, brief, module and the refresh/audit/decision tools. Also `CODEATLAS_MCP_PROFILE`. |
| `codeatlas hook session-start [--format text\|json\|cursor] [--event NAME]` | Session-start hook: consent check, catch-up update, prints the compact brief |
| `codeatlas hook user-prompt [--format ...] [--event NAME]` | Prompt hook: looks up the user's request and adds the matching code to the prompt; silent when there is nothing worth adding |
| `codeatlas hook pre-invocation` · `codeatlas hook stop` | Antigravity: the first injects the packet for the user's request as a persistent message; the second, when a value change still leaves the old value in the code, sends the agent back once with the remaining lines |
| `codeatlas hook post-edit` | Post-edit hook: starts an index update for the edited files in a detached process and returns at once; silent, always exits 0 |

`--format text` prints plain context (Claude Code); `json` prints
`{"hookSpecificOutput": {"hookEventName": ..., "additionalContext": ...}}` (Codex, Gemini CLI);
`cursor` prints `{"additional_context": ...}`. Hooks start without importing the full command
line, always speak UTF-8, and always exit 0. `CODEATLAS_HOOK_SYNC=1` makes `post-edit` wait for the
update instead of detaching.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | User error (bad input, not initialized, not found, ambiguous target) |
| 2 | Index missing or stale beyond repair |
| 3 | Internal error |

Hook commands always exit 0 so a CODEATLAS problem can never break an agent session.
