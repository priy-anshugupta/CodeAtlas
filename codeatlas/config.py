"""Project configuration: `codeatlas.toml` or `[tool.codeatlas]` in `pyproject.toml`.

Every setting has a default so a first run needs no configuration.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from codeatlas.core.errors import UserError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

DEFAULT_MAX_FILE_SIZE = 1_000_000  # bytes


@dataclass(frozen=True)
class CodeAtlasConfig:
    ignore: tuple[str, ...] = ()
    max_file_size: int = DEFAULT_MAX_FILE_SIZE
    source_roots: tuple[str, ...] = ("src",)
    test_dirs: tuple[str, ...] = ("tests", "test")
    drift_threshold: int = 8
    token_scale: float = 1.0
    extra: dict[str, Any] = field(default_factory=dict)


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise UserError(f"invalid TOML in {path.name}: {exc}") from exc


def _str_tuple(raw: dict[str, Any], key: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = raw.get(key, default)
    if not isinstance(value, (list, tuple)) or not all(isinstance(v, str) for v in value):
        raise UserError(f"codeatlas config: '{key}' must be a list of strings")
    return tuple(value)


def load_config(root: Path) -> CodeAtlasConfig:
    raw: dict[str, Any] = {}
    codeatlas_toml = root / "codeatlas.toml"
    pyproject = root / "pyproject.toml"
    if codeatlas_toml.is_file():
        raw = _read_toml(codeatlas_toml)
    elif pyproject.is_file():
        raw = _read_toml(pyproject).get("tool", {}).get("codeatlas", {})

    defaults = CodeAtlasConfig()
    max_size = raw.get("max_file_size", defaults.max_file_size)
    threshold = raw.get("drift_threshold", defaults.drift_threshold)
    scale = raw.get("token_scale", 1.0)
    if (
        isinstance(scale, bool)
        or not isinstance(scale, (int, float))
        or not math.isfinite(scale)
        or scale <= 0
    ):
        raise UserError("codeatlas config: 'token_scale' must be positive and finite")
    if not isinstance(max_size, int) or max_size <= 0:
        raise UserError("codeatlas config: 'max_file_size' must be a positive integer")
    if not isinstance(threshold, int) or threshold <= 0:
        raise UserError("codeatlas config: 'drift_threshold' must be a positive integer")
    known = {
        "ignore",
        "max_file_size",
        "source_roots",
        "test_dirs",
        "drift_threshold",
        "token_scale",
    }
    return CodeAtlasConfig(
        ignore=_str_tuple(raw, "ignore", defaults.ignore),
        max_file_size=max_size,
        source_roots=_str_tuple(raw, "source_roots", defaults.source_roots),
        test_dirs=_str_tuple(raw, "test_dirs", defaults.test_dirs),
        drift_threshold=threshold,
        token_scale=float(scale),
        extra={k: v for k, v in raw.items() if k not in known},
    )
