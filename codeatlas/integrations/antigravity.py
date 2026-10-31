"""Google Antigravity: an always-active instruction block, a pre-invocation hook, and the skill.

What Antigravity actually loads (from its own customization guide):

* `AGENTS.md` / `GEMINI.md` are always active for their directory. A rule file under
  `.agents/rules/` is only loaded unconditionally when it declares `trigger: always_on`, so the
  instruction block goes into `AGENTS.md`, where it is always seen.
* `.agents/hooks.json` can run a command before every model call (`PreInvocation`) and inject a
  `userMessage`. `codeatlas hook pre-invocation` uses that to deliver the packet for the user's request
  without the agent having to remember to ask for it.
* Skills in `.agents/skills/` are only listed by name and description until the model opens one.
* MCP servers are read from `~/.gemini/config/mcp_config.json`, a user-level file that CODEATLAS never
  edits on its own: `init` prints the entry to add.
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from codeatlas.integrations.base import (
    FileChange,
    Integration,
    IntegrationOptions,
    dump_json,
    load_json,
    read_text,
    with_block,
    without_block,
)
from codeatlas.integrations.common import MCP_ENTRY, instruction_block, skill_files

AGENTS_MD = "AGENTS.md"
HOOKS = ".agents/hooks.json"
SKILL = ".agents/skills/codeatlas-context/SKILL.md"
LEGACY_RULE = ".agent/rules/codeatlas.md"  # written by earlier versions; never loaded unconditionally
USER_MCP_FILE = "~/.gemini/config/mcp_config.json"
HOOK_NAME = "codeatlas"
HOOK_ENTRY: dict[str, Any] = {
    "PreInvocation": [
        {"type": "command", "command": "codeatlas hook pre-invocation", "timeout": 20},
    ],
    "Stop": [
        {"type": "command", "command": "codeatlas hook stop", "timeout": 20},
    ],
}


AGY_TIMEOUT = 30
USER_MCP_COMMAND = ["mcp", "add", "codeatlas", "codeatlas", "mcp"]


def _agy(*args: str) -> subprocess.CompletedProcess[str] | None:
    agy = shutil.which("agy")
    if agy is None:
        return None
    try:
        return subprocess.run(
            [agy, *args], capture_output=True, text=True, timeout=AGY_TIMEOUT, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def user_mcp_registered() -> bool | None:
    """Is a `codeatlas` server in Antigravity's user-level MCP list? None when agy is unavailable."""
    listed = _agy("mcp", "list")
    if listed is None or listed.returncode != 0:
        return None
    return any(line.split()[:1] == ["codeatlas"] for line in listed.stdout.splitlines())


def register_user_mcp() -> bool:
    """Add `codeatlas mcp` to Antigravity's user-level MCP list (only when the user agreed)."""
    added = _agy(*USER_MCP_COMMAND)
    return added is not None and added.returncode == 0


def unregister_user_mcp() -> bool:
    """Remove the user-level `codeatlas` server, only if it is the one `codeatlas init` adds."""
    listed = _agy("mcp", "list")
    if listed is None or not any(
        line.split()[:1] == ["codeatlas"] and "codeatlas mcp" in line for line in listed.stdout.splitlines()
    ):
        return False
    removed = _agy("mcp", "remove", "codeatlas")
    return removed is not None and removed.returncode == 0


def _without_codeatlas_hook(config: dict[str, Any]) -> dict[str, Any]:
    data = copy.deepcopy(config)
    data.pop(HOOK_NAME, None)
    return data


class AntigravityIntegration(Integration):
    name = "antigravity"

    def detect(self, root: Path) -> bool:
        return (root / ".agent").is_dir() or (root / ".agents").is_dir()

    def plan(self, root: Path, options: IntegrationOptions) -> list[FileChange]:
        changes = [
            FileChange(
                AGENTS_MD,
                with_block(read_text(root / AGENTS_MD), instruction_block(options.mcp)),
                "CODEATLAS instruction block (always active)",
            ),
            *[
                FileChange(
                    (Path(SKILL).parent / relative).as_posix(), content, "codeatlas-context resource"
                )
                for relative, content in skill_files("codeatlas-context")
            ],
        ]
        config = load_json(root / HOOKS)
        new = _without_codeatlas_hook(config)
        if options.hooks:
            new[HOOK_NAME] = copy.deepcopy(HOOK_ENTRY)
        if new != config:
            changes.append(FileChange(HOOKS, dump_json(new) if new else None, "PreInvocation hook"))
        if (root / LEGACY_RULE).is_file() and "codeatlas-managed" in (
            read_text(root / LEGACY_RULE) or ""
        ):
            changes.append(FileChange(LEGACY_RULE, None, "old CODEATLAS rule (replaced by AGENTS.md)"))
        return [c for c in changes if not c.is_noop(root)]

    def plan_removal(self, root: Path) -> list[FileChange]:
        changes: list[FileChange] = []
        if (root / AGENTS_MD).is_file():
            changes.append(
                FileChange(AGENTS_MD, without_block(read_text(root / AGENTS_MD)), "CODEATLAS block")
            )
        if (root / HOOKS).is_file():
            remaining = _without_codeatlas_hook(load_json(root / HOOKS))
            changes.append(
                FileChange(HOOKS, dump_json(remaining) if remaining else None, "CODEATLAS hook")
            )
        resources = [
            ((Path(SKILL).parent / relative).as_posix(), "codeatlas-context resource")
            for relative, _ in skill_files("codeatlas-context")
        ]
        for path, detail in [*resources, (LEGACY_RULE, "old CODEATLAS rule")]:
            if (root / path).is_file():
                changes.append(FileChange(path, None, detail))
        return [c for c in changes if not c.is_noop(root)]

    def notes(self, root: Path, options: IntegrationOptions) -> list[str]:
        if not options.mcp or user_mcp_registered():
            return []
        entry = json.dumps({"mcpServers": {"codeatlas": MCP_ENTRY}}, indent=2)
        return [
            f"Antigravity reads MCP servers from {USER_MCP_FILE} (user-level; CODEATLAS does not edit "
            f"it). To give it the CODEATLAS tools, add:\n{entry}"
        ]

    def status(self, root: Path) -> list[tuple[str, bool | None, str]]:
        block = read_text(root / AGENTS_MD) or ""
        if "codeatlas-managed" not in block and "CODEATLAS code index" not in block:
            return []
        hooks = read_text(root / HOOKS) or ""
        return [
            ("antigravity instructions", True, "AGENTS.md block installed"),
            (
                "antigravity hook",
                True if "codeatlas hook pre-invocation" in hooks else None,
                "PreInvocation hook installed"
                if "codeatlas hook pre-invocation" in hooks
                else "not installed (optional)",
            ),
        ]
