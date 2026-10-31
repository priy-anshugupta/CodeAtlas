"""Toolchain detection for the audit plan (shared with the brief; see
`codeatlas.extractors.toolchain`). Detection only: CODEATLAS never runs these. The audit skill
decides which are safe to run and asks the user about anything needing network/DB/Docker.
"""

from __future__ import annotations

from codeatlas.extractors.toolchain import detect_toolchain

__all__ = ["detect_toolchain"]
