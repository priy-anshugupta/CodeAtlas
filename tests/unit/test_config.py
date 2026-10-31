from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas.config import CodeAtlasConfig, load_config
from codeatlas.core.errors import UserError
from codeatlas.core.tokens import estimate_tokens


def test_defaults_without_config(tmp_path: Path) -> None:
    assert load_config(tmp_path) == CodeAtlasConfig()


def test_pyproject_tool_codeatlas(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.codeatlas]\nignore = ["gen/"]\nmax_file_size = 10\nsource_roots = ["lib"]\n'
    )
    cfg = load_config(tmp_path)
    assert cfg.ignore == ("gen/",)
    assert cfg.max_file_size == 10
    assert cfg.source_roots == ("lib",)


def test_codeatlas_toml_wins_over_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.codeatlas]\nignore = ["a"]\n')
    (tmp_path / "codeatlas.toml").write_text('ignore = ["b"]\n')
    assert load_config(tmp_path).ignore == ("b",)


@pytest.mark.parametrize(
    "body", ['ignore = "notalist"', "max_file_size = -1", "drift_threshold = 0", "ignore = ["]
)
def test_invalid_config_is_a_user_error(tmp_path: Path, body: str) -> None:
    (tmp_path / "codeatlas.toml").write_text(body + "\n")
    with pytest.raises(UserError):
        load_config(tmp_path)


def test_optional_token_scale_is_pure_and_default_is_unchanged(tmp_path: Path) -> None:
    assert estimate_tokens("abcde") == 2
    assert estimate_tokens("abcde", 2) == 3
    (tmp_path / "codeatlas.toml").write_text("token_scale = 1.3\n", encoding="utf-8")
    assert load_config(tmp_path).token_scale == 1.3
    (tmp_path / "codeatlas.toml").write_text("token_scale = -1\n", encoding="utf-8")
    with pytest.raises(UserError, match="token_scale"):
        load_config(tmp_path)
