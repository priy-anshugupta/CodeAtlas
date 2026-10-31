"""Classify disposable-cache failures consistently across CLI, MCP, and hooks."""

from __future__ import annotations

import sqlite3

from codeatlas.core.errors import CodeAtlasError


class IndexQueryError(CodeAtlasError):
    code = "index_error"


class IndexBusyError(CodeAtlasError):
    code = "index_busy"


def database_problem(exc: sqlite3.DatabaseError) -> CodeAtlasError | None:
    code = getattr(exc, "sqlite_errorcode", 0) & 0xFF
    if code in (sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB):
        return None  # only these errors justify destructive disposable-cache recovery
    if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
        return IndexBusyError(
            "Index is busy updating; retry at most once, then use bounded local search.",
            retryable=True,
        )
    return IndexQueryError(
        "CODEATLAS retrieval failed; use bounded local search, without repeating the lookup or rebuilding.",
        cause=type(exc).__name__,
        retryable=False,
    )
