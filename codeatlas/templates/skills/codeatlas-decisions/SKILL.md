---
name: codeatlas-decisions
description: Read or record the rationale for a repository design decision when the user asks for decision history or explicitly makes a decision.
disable-model-invocation: true
---
<!-- codeatlas-managed: installed and updated by `codeatlas init`. Local edits are overwritten on upgrade. -->

# CODEATLAS Decision Memory

## Purpose

Decisions explain *why* the code is the way it is. CODEATLAS keeps them as short, dated notes in `.aicontext/decisions/` so a future session can find the reason instead of re-arguing it. `codeatlas search` indexes them.

## When to use

- The user settles a design question in conversation and wants it remembered.
- The user asks you to record, update, or supersede a decision.
- Before changing something that looks deliberate: check whether a decision explains it.

## Preconditions

1. `codeatlas status` (MCP: `codeatlas_status`) shows CODEATLAS **enabled**. If not, don't record anything and don't enable CODEATLAS yourself; tell the user.
2. Record a decision only when the user made it or explicitly asked you to record it. Never invent decisions from your own guesses about the code.

## Procedure

1. **Check what exists.** `codeatlas decision list` (MCP: `codeatlas_decisions`), or `codeatlas search "<topic>"` to find related decisions. Read the relevant one with `codeatlas decision show <id>`.
2. **Write it down.** `codeatlas decision add --title "<decision in one line>" --context "<problem and forces>" --decision "<what and why>" [--consequences "<trade-offs, follow-ups>"] [--symbol <id>] [--supersedes <id>]` (MCP: `codeatlas_decision_record`).
   - Title states the choice, e.g. "Store money as integer cents".
   - Context: the problem, constraints, and alternatives considered, in 1–4 sentences.
   - Decision: what was chosen and the main reason.
   - Consequences: what this makes easier or harder; follow-up work.
   - Use `--supersedes` when a new decision replaces an old one; CODEATLAS marks the old one superseded.
3. **Confirm** to the user in one sentence, with the decision id.

## Outputs

- A new `.aicontext/decisions/NNNN-<slug>.md` note, searchable with `codeatlas search`.

## Guardrails

- Keep each decision under ~600 tokens: it's a note, not a design doc.
- Only facts from the conversation or verified in code. No speculation.
- Never edit decision files by hand, and never delete them; supersede instead.
- Never run `codeatlas init`, `codeatlas scan`, or `codeatlas enable` unless the user asks.
