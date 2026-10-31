# Configuration

CODEATLAS works with no configuration. Everything here is optional.

## Project settings

Put settings in `codeatlas.toml` at the repository root, or under `[tool.codeatlas]` in
`pyproject.toml`. If both exist, `codeatlas.toml` wins.

```toml
# pyproject.toml
[tool.codeatlas]
ignore = ["generated/", "*.pb.py"]   # gitignore syntax, on top of .gitignore and .codeatlasignore
max_file_size = 1000000              # bytes; larger files are skipped
source_roots = ["src"]               # stripped when deriving module names
test_dirs = ["tests", "test"]        # folders whose files count as tests
drift_threshold = 8                  # drift points before a brief section is marked stale
semantic = false                     # true: blend local embeddings into `codeatlas task` and hooks
semantic_model = "/models/all-MiniLM-L6-v2"   # local model path or cached model name
worklog = true                       # remember requests, edits and notes for the next session
prompt_context = true                # let the prompt hook add the code a request needs
prompt_budget = 2000                 # hard cap; starts small and expands for complete evidence
```

| Key | Type | Default | Effect |
|---|---|---|---|
| `ignore` | list of strings | `[]` | Extra ignore patterns in `.gitignore` syntax |
| `max_file_size` | positive integer | `1000000` | Files larger than this many bytes are not indexed |
| `source_roots` | list of strings | `["src"]` | Prefixes removed from paths when deriving module ids (`src/shop/cart.py` → `shop.cart`) |
| `test_dirs` | list of strings | `["tests", "test"]` | Directory names whose files are treated as tests |
| `drift_threshold` | positive integer | `8` | Score at which an `AGENTS.md` section or module summary becomes stale |
| `semantic` | boolean | `false` | `true` adds local embeddings as a third retrieval channel in `codeatlas task` and the prompt hook (needs `codeatlas-ctx[semantic]` and a local model). `CODEATLAS_SEMANTIC=1/0` overrides |
| `semantic_model` | string | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model for `semantic` and `search --semantic`; a local path or a model already in the Hugging Face cache. CODEATLAS never downloads |
| `worklog` | boolean | `true` | `false` stops recording requests, edited files and notes in `.aicontext/cache/worklog/` (local, gitignored); `CODEATLAS_WORKLOG=0` overrides |
| `prompt_context` | boolean | `true` | `false` stops `codeatlas hook user-prompt` from adding anything to prompts |
| `prompt_budget` | integer | `2000` | Hard cap as `ceil(characters/4)` (128-8000); starts at 1200 and expands only if it completes the evidence |

Invalid values stop the command with a clear error rather than being silently ignored.

## Ignoring files

CODEATLAS combines, in order:

1. **Built-in ignores:** version-control folders, `.aicontext/`, virtual environments,
   `node_modules`, caches, `build`, `dist`, `target`, `coverage`, `vendor`, editor folders and
   `*.egg-info`.
2. **`.gitignore` files**, each scoped to its own directory, with `!pattern` re-includes honoured
   the way git does.
3. **`.codeatlasignore`** at the root, in the same syntax, for things you want in git but not in the
   index.
4. **`ignore`** from the configuration above.

Binary files, files over `max_file_size`, minified bundles (`*.min.js`, `*.bundle.js`, source
maps, or JavaScript/TypeScript that reads as minified) and unrecognised file types are skipped
automatically.

## Languages

| Language | Parser | Install |
|---|---|---|
| Python | stdlib `ast` | built in |
| JavaScript, TypeScript (incl. JSX/TSX) | tree-sitter | `pip install "codeatlas-ctx[treesitter]"` |
| Go, Java | tree-sitter | `pip install "codeatlas-ctx[treesitter]"` |
| Dart, Kotlin, Swift | built-in declaration scanner (classes, functions, methods, imports, calls) | built in |
| Rust, Ruby, PHP, C#, C, C++, Scala, shell, SQL | none yet | counted in the language stats, not parsed |

`codeatlas doctor` shows which languages were found and which are parsed.

## Environment variables

| Variable | Effect |
|---|---|
| `CODEATLAS_CONFIG_HOME` | Where the per-user consent registry lives (default `~/.config/codeatlas`). Point it at a scratch folder for experiments and tests. |
| `CODEATLAS_VIEWER_LOG=1` | Log every viewer HTTP request to the terminal. |
| `CODEATLAS_UPDATE_GOLDEN=1` | Development only: regenerate golden files when running the tests. |
| `CODEATLAS_HOOK_NO_EXIT=1` | Development only: let hook commands return normally instead of exiting the process, for in-process testing. |
| `CODEATLAS_HOOK_SYNC=1` | Make `codeatlas hook post-edit` wait for the index update instead of starting it in a detached process. |
| `CODEATLAS_PROMPT_CONTEXT=0` | Switch off what `codeatlas hook user-prompt` adds to prompts, for you, in every repository. |
| `CODEATLAS_MCP_PROFILE=full` | Expose every MCP tool (default `lean`: `codeatlas_task` only; `standard` adds status, context, impact). |
| `CODEATLAS_DAEMON=0` | Never use or start the warm query process (below). |
| `CODEATLAS_FEEDBACK=0` | Do not record or use ranking feedback from edits (below). |
| `CODEATLAS_SESSION` | A session id for `codeatlas task`: code already returned in this session comes back as a reference. |
| `CODEATLAS_PROFILE=1` | Opt into local navigator timing/counter records in `query-metrics.jsonl` under the local cache directory. Records contain a query hash and estimates, not query/source text. They exclude launcher/freshness work and billing; the file rotates at 1 MiB. |

## Per-user state

| File | Contents |
|---|---|
| `~/.config/codeatlas/repos.toml` | Which repositories CODEATLAS is enabled or paused in, for you |
| Your agent's global instructions (for example `~/.claude/CLAUDE.md`) | Only if you ran `codeatlas install --global` |

Nothing else is written outside the repositories you enable.

## Semantic retrieval

Lexical retrieval finds what a request names. With `semantic = true`, `codeatlas task` also finds
code a request only *describes* ("split a list into fixed-size groups" → `chunk`). It is
optional and local:

1. `pip install codeatlas-ctx[semantic]` (NumPy, `tokenizers`, `safetensors`; no PyTorch).
2. Have the model on disk once, e.g. `huggingface-cli download sentence-transformers/all-MiniLM-L6-v2`.
   CODEATLAS never downloads anything.
3. Set `semantic = true` in `[tool.codeatlas]`.

BERT encoders with mean pooling (the default model family) run on NumPy alone and load in well
under a second; other models need `codeatlas-ctx[semantic-full]` (sentence-transformers). Symbol
vectors are cached in `.aicontext/cache/vectors-*.npz` by the hash of the embedded text, so
updates re-embed only changed symbols. The first build runs in the background after `scan` and
updates (about 30 ms per symbol on a laptop CPU); until it exists, answers are purely lexical.
Similarity can raise a block both channels agree on and, when the request names nothing
exactly, add up to two strongly similar symbols, which are marked `similar` and never yield more
than `medium` confidence.

## Prompt hook options

| Key | Default | Effect |
|---|---|---|
| `prompt_context` | `true` | Add the answer to the user's request to the prompt |
| `prompt_overview` | `true` | Also answer "explain the architecture" requests with the map (silent when the map would be empty) |
| `prompt_budget` | `2000` | Hard cap, in tokens, for what the hook adds |
| `ranking_feedback` | `true` | Rank files an agent edited slightly higher (see below) |
| `daemon` | `true` | Allow the warm query process |

`CODEATLAS_DEDUPE=0` switches the opt-in read dedupe off for you.

## Warm query process

After the first `codeatlas task` in a repo where CODEATLAS is enabled and not paused, a small background
process keeps the index loaded and answers later `codeatlas task` calls (about 0.6 s end to end instead
of about 1.2 s). It listens only on a local named pipe or Unix socket protected by a random key
(`.aicontext/cache/daemon.json`), never on a network port; it exits after 10 idle minutes and as
soon as you pause, disable or uninstall. If it is unreachable, the command answers itself with
identical output. Off with `daemon = false` in `[tool.codeatlas]` or `CODEATLAS_DAEMON=0`.
See `docs/adr/0003-warm-query-process.md`.

## Ranking feedback

Files an agent edited rank slightly higher for later requests (at most +25%, halving every 30
days, never above an exact name match). The table is a local cache,
`.aicontext/cache/ranking_feedback.json`. Off with `ranking_feedback = false` or
`CODEATLAS_FEEDBACK=0`; ranking is then exactly the unboosted one. See `docs/adr/0005-local-ranking-feedback.md`.

## Work log

Hooks record, per agent session, the requests, the files edited (with the first line of each
edit, resolved to the enclosing function when shown) and the symbols retrieved; agents can add
one-line handoff notes with `codeatlas note`. The next session-start brief includes a summary of
the most recent other session (at most about 140 tokens), `codeatlas task` answers mention earlier
work on the same code when it fits the budget, and `codeatlas recall` searches older sessions. The
log is local to you (`.aicontext/cache/worklog/`, gitignored), pruned after 30 days, and
written only where CODEATLAS is enabled for you and not paused.
