from pathlib import Path

import pytest

from codeatlas.integrations import IntegrationOptions, get_integration


def test_mcp_server_instructions_do_not_override_hook_reuse() -> None:
    from codeatlas.instructions import SHORT
    from codeatlas.mcp.server import INSTRUCTIONS

    # Reuse stays the first rule: MCP replaces grep and reads only for code not yet delivered.
    assert INSTRUCTIONS.startswith(SHORT) and "you don't have yet" in INSTRUCTIONS


@pytest.mark.parametrize(
    ("agent", "path"),
    [
        ("codex", "AGENTS.md"),
        ("claude-code", "CLAUDE.md"),
        ("gemini", "GEMINI.md"),
        ("cursor", ".cursor/rules/codeatlas.mdc"),
        ("antigravity", "AGENTS.md"),
    ],
)
@pytest.mark.parametrize("mcp", [False, True])
def test_installed_guidance_uses_selected_transport(
    tmp_path: Path, agent: str, path: str, mcp: bool
) -> None:
    changes = get_integration(agent).plan(tmp_path, IntegrationOptions(mcp=mcp))
    text = next(change.content for change in changes if change.path == path)
    assert text is not None
    from codeatlas.instructions import LOCATED, RECOVERY, SHORT

    assert SHORT in text and LOCATED in text
    assert RECOVERY in text  # transport failure must allow bounded ordinary investigation
    if mcp:
        assert "MCP `codeatlas_task` for code you lack" in text
        assert 'codeatlas task "' not in text
    else:
        assert 'codeatlas task "<user request>"' in text
        assert "MCP `codeatlas_task`" not in text
