# Security policy

## Supported versions

CODEATLAS is pre-1.0. Security fixes go into the latest release and `main`.

| Version | Supported |
|---|---|
| 0.1.x | Yes |
| < 0.1 | No |

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report privately through GitHub's
[private vulnerability reporting](https://github.com/priy-anshugupta/CodeAtlas/security/advisories/new)
for this repository. Include:

- the CODEATLAS version (`codeatlas --version`), OS and Python version;
- what an attacker can do, and the conditions needed;
- steps or a minimal repository to reproduce;
- any suggested fix.

You can expect an acknowledgement within a few days. We will keep you updated on the fix, agree a
disclosure date with you, and credit you unless you prefer otherwise.

## Security model

CODEATLAS is designed to run locally with a small attack surface. Reports that break any of these
guarantees are especially welcome:

| Guarantee | Where it is enforced |
|---|---|
| No network calls from CODEATLAS's core; no telemetry | Sockets are blocked for the whole test suite |
| No API keys; CODEATLAS never calls a language model | Architecture (CLAUDE.md §3) |
| CODEATLAS never modifies your source code | Only `codeatlas/writers/` writes, and only into `.aicontext/`; integrations write only their own config files, with backups |
| Nothing runs in a repository you haven't enabled, per user | Consent checks in every hook and in the MCP server |
| The graph viewer is local only | Binds to `127.0.0.1`, requires a per-session token, checks the `Host` header, sends a strict Content-Security-Policy, and exposes no endpoint that runs commands or writes outside `.aicontext/cache/` |
| The MCP server cannot run commands | Tools wrap library functions; writes are limited to findings, narrative sections and decisions inside `.aicontext/` |
| Hooks cannot break an agent session | They always exit 0 and log errors to `.aicontext/cache/hook.log` instead of printing them |

## Things to keep in mind

- `.aicontext/` is meant to be committed. It contains symbol names, signatures, docstrings, file
  paths and, if you run audits, finding descriptions. Review it like any other file before
  pushing to a public repository.
- Audit evidence is capped in length and the audit skill is instructed never to print secrets,
  but review findings before sharing them.
- Static smell detection flags patterns that look like hard-coded secrets. Treat those leads
  seriously; CODEATLAS itself never transmits them anywhere.
