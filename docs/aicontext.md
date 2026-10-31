# The `.aicontext/` directory

Everything CODEATLAS knows about a repository lives in `.aicontext/` as plain JSON and Markdown.
Any tool can read it with a file read; no CODEATLAS install is needed to use it.

- [Layout](#layout)
- [Committing it](#committing-it)
- [Artifacts](#artifacts)
- [AGENTS.md](#agentsmd)
- [Module summaries](#module-summaries)
- [Schemas and versions](#schemas-and-versions)
- [Rules for agents and tools](#rules-for-agents-and-tools)

## Layout

```text
.aicontext/
├── AGENTS.md                ≤ 600-token session brief (facts by CODEATLAS, narrative by your agent)
├── manifest.json            versions, per-file hashes, artifact hashes, drift state, stats
├── symbols.json             every function, class and method
├── dependency_graph.json    module import graph, external and declared dependencies, entry points
├── call_graph.json          symbol call graph with resolution confidence and PageRank
├── blast_radius.json        reverse transitive dependents per file and public symbol (capped)
├── tests_map.json           symbol and file → related tests
├── routes.json              HTTP routes → handler symbols
├── models.json              ORM and data models → fields → usages
├── config.json              config keys and environment variables → where they are read
├── health.json              per-file and per-symbol risk, smells, dead-code candidates
├── git_intelligence.json    churn, ownership, co-change pairs (empty without git)
├── modules/<group>.md       per-module summaries, loaded on demand
├── decisions/               architecture decision records (codeatlas decision add)
├── audit/
│   ├── audit_plan.json      from codeatlas audit plan
│   ├── findings.json        the canonical findings store
│   ├── REPORT.md            from codeatlas audit report
│   ├── history/             previous reports, for diffing
│   └── scratch/             repro tests written during an audit       (gitignored)
└── cache/                                                            (gitignored)
    ├── index-<fingerprint>.sqlite   read-only query cache, rebuilt from the JSON when missing
    ├── state.sqlite                 parse cache and incremental state
    ├── activity.log                 ids the agent looked at, for the viewer's activity trail
    ├── layout.json, views/          saved viewer layout and views
    └── backups/                     copies of files modified by codeatlas init
```

## Committing it

`.aicontext/` is meant to be committed: one scan benefits every teammate and every AI session, and
because output is deterministic, diffs show real structural change. `codeatlas init` adds
`.aicontext/cache/` and `.aicontext/audit/scratch/` to `.gitignore`.

Committed files never enable CODEATLAS for anyone; see [consent](agents.md#consent).

## Artifacts

### `symbols.json`

One entry per function, class and method:

```json
{
  "id": "shop.checkout.cart.BaseCart",
  "kind": "class",
  "module": "shop.checkout.cart",
  "parent": null,
  "file": "src/shop/checkout/cart.py",
  "lines": [8, 16],
  "signature": "class BaseCart",
  "doc": "",
  "decorators": [],
  "visibility": "public",
  "calls": [],
  "called_by": [],
  "rank": 0.017435,
  "tokens_est": 57
}
```

| Field | Meaning |
|---|---|
| `id` | Fully qualified id: `package.module.Class.method` |
| `kind` | `function`, `method`, `class`, … |
| `lines` | First and last line, 1-based and inclusive |
| `doc` | First line of the docstring or doc comment |
| `visibility` | `public` or `private` (leading underscore or language rules) |
| `calls` / `called_by` | Resolved call edges, by symbol id |
| `rank` | PageRank importance in the call graph |
| `tokens_est` | Estimated tokens to read the symbol (characters ÷ 4) |

### Graphs

| File | Top-level keys |
|---|---|
| `dependency_graph.json` | `modules` (id, file, doc, loc, rank, community, imports, imported_by, external, is_package, entry_point), `edges` (`from`, `to`), `external`, `declared_dependencies`, `entry_points` |
| `call_graph.json` | `edges` (`from`, `to`, `line`, `confidence`: `high` / `medium` / `low`), `rank`, `stats` |
| `blast_radius.json` | `files` and `symbols`: dependent `count` and `top` dependents |

### Extractor outputs

| File | Top-level keys |
|---|---|
| `tests_map.json` | `test_files`, `by_file`, `by_symbol` |
| `routes.json` | `routes`: method, path, handler, file, line, framework |
| `models.json` | `models`: fields and usages |
| `config.json` | `keys`: config keys and env vars with every read location |
| `health.json` | `files` and `symbols` (complexity, churn, coverage, centrality, smells, risk and the reasons for it), `smell_counts`, `dead_code` |
| `git_intelligence.json` | `available`, `head`, `commits_analyzed`, `churn`, `owners`, `co_change`, `last_changed` |

### `manifest.json`

The only file with timestamps. Keys: `repo_id`, `created`, `last_scan`, `codeatlas_version`,
`schema_version`, `files` (SHA-256, size, mtime and language per source file), `artifacts`
(content hash per artifact), `drift` (score, staleness and pending changes per section),
`rank_approx` (true while ranking is approximate after incremental updates), and `stats`.

## AGENTS.md

The brief is a hybrid document. CODEATLAS owns the **generated** regions and rewrites them on every
scan; your agent owns the **narrative** regions, which CODEATLAS never overwrites.

```markdown
# <project> — Agent Brief

## Facts
<!-- codeatlas:generated:facts -->
- Languages, key dependencies, entry points, commands (test / lint / typecheck),
  top modules by importance, size (the file keeps these; the injected brief uses only
  languages and commands)
<!-- /codeatlas:generated:facts -->

## Purpose
<!-- codeatlas:narrative:purpose -->
What the project does and for whom (2–3 sentences).
<!-- /codeatlas:narrative:purpose -->

## Architecture
<!-- codeatlas:narrative:architecture -->
How the pieces fit and the main data flow.
<!-- /codeatlas:narrative:architecture -->

## Conventions
<!-- codeatlas:narrative:conventions -->
Patterns to follow, gotchas.
<!-- /codeatlas:narrative:conventions -->

## Navigation
<!-- codeatlas:generated:navigation -->
Start with `codeatlas task "<request>"` …; follow up with `codeatlas context` / `codeatlas impact`.
<!-- /codeatlas:generated:navigation -->
```

Narrative sections start as a placeholder and stay one unless someone writes them (by hand, or
through the optional `codeatlas-refresh` skill). Updates go through `codeatlas refresh commit`, which
validates the markers and the token limit; the whole file must stay within 600 tokens.

**What an agent is actually shown** is the compact brief (`codeatlas brief`, and the session-start
hook): the title, the `Languages` and `Commands` facts, any narrative section that has been
written, and one line on how to use CODEATLAS, typically 100-150 tokens. Placeholders, key
dependencies, entry points and module rankings are not injected: a repository overview does not
help an agent find files faster, and a study of context files found they raise cost by about
20% without improving success. `codeatlas brief --full` prints the whole file.

In monorepos, commands are detected per application and prefixed with the folder, for example
`test (backend): cd backend && python manage.py test`.

## Module summaries

`modules/<group>.md` holds one summary per module group. A generated facts region lists the
files, the docstring, the public API by importance (signature, first doc line, location), what
the group depends on and is used by, and its tests. A `summary` narrative region is written by
the agent through `codeatlas-refresh`. Agents load summaries on demand with `codeatlas module <name>`;
they are never injected automatically.

```markdown
# Module `shop.pricing`

<!-- codeatlas:generated:facts -->
- Files: src/shop/pricing/__init__.py, src/shop/pricing/discounts.py, src/shop/pricing/rules.py
- Public API (by importance):
  - `apply_discount(amount: Money, …) -> Money` — Apply the best eligible discount to an amount. (src/shop/pricing/discounts.py:8)
- Depends on: `shop`
- Used by: `shop.checkout`
- Tests: tests/test_discounts.py
<!-- /codeatlas:generated:facts -->

## Summary
<!-- codeatlas:narrative:summary -->
_Not written yet. Run the codeatlas-refresh skill to fill this section._
<!-- /codeatlas:narrative:summary -->
```

## Schemas and versions

Every JSON artifact carries `schema_version`. JSON Schemas for all of them live in
[`codeatlas/schemas/`](../codeatlas/schemas) and are validated in the test suite, together with the
schema for finding input (`finding_input.schema.json`) and the audit plan.

A breaking schema change bumps the major version and ships a migration; run `codeatlas migrate` after
upgrading CODEATLAS when `codeatlas doctor` or `codeatlas status` asks for it.

## Rules for agents and tools

- Read `AGENTS.md`, then query through `codeatlas search` / `context` / `impact` or the MCP tools.
  Don't load whole JSON artifacts into a model's context; that defeats the purpose.
- Never hand-edit `.aicontext/`. CODEATLAS rewrites generated content, and hand edits are repaired on
  the next full scan.
- Narrative changes go through `codeatlas refresh commit`; findings through `codeatlas audit record`.
