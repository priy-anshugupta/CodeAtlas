"""Antigravity's user-level MCP list: read, added to and removed from only through `agy`."""

from __future__ import annotations

import subprocess

import pytest

from codeatlas.integrations import antigravity


class FakeAgy:
    def __init__(self, listing: str) -> None:
        self.listing = listing
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args: str) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[:2] == ("mcp", "list"):
            return subprocess.CompletedProcess(args, 0, self.listing, "")
        return subprocess.CompletedProcess(args, 0, "", "")


def test_registration_is_detected_from_the_listing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(antigravity, "_agy", FakeAgy("No MCP servers configured."))
    assert antigravity.user_mcp_registered() is False
    monkeypatch.setattr(antigravity, "_agy", FakeAgy("NAME TYPE\ncodeatlas stdio enabled codeatlas mcp\n"))
    assert antigravity.user_mcp_registered() is True
    monkeypatch.setattr(antigravity, "_agy", lambda *args: None)  # agy not installed
    assert antigravity.user_mcp_registered() is None


def test_register_runs_the_documented_command(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeAgy("")
    monkeypatch.setattr(antigravity, "_agy", fake)
    assert antigravity.register_user_mcp() is True
    assert fake.calls == [("mcp", "add", "codeatlas", "codeatlas", "mcp")]


def test_only_codeatlass_own_entry_is_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    someone_elses = FakeAgy("codeatlas stdio enabled C:/tools/other-server.exe\n")
    monkeypatch.setattr(antigravity, "_agy", someone_elses)
    assert antigravity.unregister_user_mcp() is False
    assert ("mcp", "remove", "codeatlas") not in someone_elses.calls
    ours = FakeAgy("codeatlas stdio enabled codeatlas mcp\n")
    monkeypatch.setattr(antigravity, "_agy", ours)
    assert antigravity.unregister_user_mcp() is True
    assert ours.calls[-1] == ("mcp", "remove", "codeatlas")
