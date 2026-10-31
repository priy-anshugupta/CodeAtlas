---
name: codeatlas-refresh
description: Refresh CODEATLAS narrative summaries when the user asks or the project brief has drifted after structural changes.
disable-model-invocation: true
---
<!-- codeatlas-managed: installed and updated by `codeatlas init`. Local edits are overwritten on upgrade. -->

# CODEATLAS Narrative Refresh

## Purpose

CODEATLAS keeps the factual parts of `.aicontext/AGENTS.md` and `.aicontext/modules/*.md` current on its own. The **narrative** parts (purpose, architecture, conventions, module explanations) are written by you, the host agent, and only when CODEATLAS's drift score says the code changed meaningfully. This keeps the brief accurate without spending tokens on every edit.

## When to use

- `codeatlas status` / the session brief reports stale sections. Offer this **after** finishing the user's current task, not in the middle of it.
- The user asks to refresh, update, or rewrite the project brief or a module summary.

## Preconditions

1. `codeatlas status` (MCP: `codeatlas_status`) shows CODEATLAS **enabled**. If it isn't, stop and tell the user; don't enable it yourself.
2. If files changed since the last update, run `codeatlas update` first so the refresh is based on current code.
3. If no sections are stale and the user didn't ask explicitly, stop and say the brief is up to date.

## Procedure

1. **Get the refresh packet.** `codeatlas refresh prepare [--sections <names>]` (MCP: `codeatlas_refresh_prepare`). For each stale section it gives:
   - the current text,
   - the structural diff since the section was last written (added/removed modules, public API changes, new routes/models/config, new dependencies),
   - context packs for the symbols involved,
   - the section's token limit.
2. **Read only what the packet points to.** Use `codeatlas context <target>` for anything you need to understand better. Don't scan the repo.
3. **Rewrite each section.**
   - Keep what's still true, fix what the diff made wrong, add what's new. Don't reword correct text.
   - Stay under the section's token limit; the whole `AGENTS.md` must stay ≤ 600 tokens.
   - Write for an AI agent starting a fresh session: concrete names, file paths, commands, data flow, and gotchas. No marketing, filler, or history unless it prevents a likely mistake.
   - Include only facts you verified in code or the packet.
4. **Commit each section through CODEATLAS.** Save the text to `.aicontext/cache/refresh/<section>.md` and run `codeatlas refresh commit <section> --file <path>` (MCP: `codeatlas_refresh_commit` with the text). CODEATLAS checks markers and length and resets that section's drift. If it rejects the text, fix the reported problem and retry.
5. **Report** in one or two sentences which sections you refreshed and what changed materially.

### What each section should answer

| Section | Should answer |
|---|---|
| `purpose` | What the project does and for whom, in 2–3 sentences. |
| `architecture` | Main components, how a request/data flows through them, where state lives. |
| `conventions` | Patterns to follow (error handling, naming, layering, testing) and traps to avoid. |
| `modules/<name>` | What the module is responsible for, its key entry points, what depends on it, and what not to do in it. |

## Outputs

- Updated narrative regions in `.aicontext/AGENTS.md` and/or `.aicontext/modules/<name>.md`.
- Drift reset for each committed section.
- A short summary to the user.

## Guardrails

- Never edit `AGENTS.md` or module files directly, and never touch `<!-- codeatlas:generated:* -->` regions. Write only through `codeatlas refresh commit`.
- Never exceed token limits; shorter and correct beats longer.
- Don't guess. If you can't verify something, leave it out.
- Never run `codeatlas init`, `codeatlas scan`, or `codeatlas enable` unless the user asks.
