"""The only package that writes into `.aicontext/`.

Names are imported on first use: a hook that only needs the manifest should not pay for the
drift, artifact and Markdown writers (tens of milliseconds, on every edit).
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from codeatlas.writers.index_writer import write_index
    from codeatlas.writers.manifest import load_manifest, new_manifest, write_manifest

_HOME = {
    "write_index": "codeatlas.writers.index_writer",
    "load_manifest": "codeatlas.writers.manifest",
    "new_manifest": "codeatlas.writers.manifest",
    "write_manifest": "codeatlas.writers.manifest",
}


def __getattr__(name: str) -> Any:
    module = _HOME.get(name)
    if module is None:
        raise AttributeError(f"module 'codeatlas.writers' has no attribute {name!r}")
    return getattr(importlib.import_module(module), name)


__all__ = ["load_manifest", "new_manifest", "write_index", "write_manifest"]
