"""Is the installed `codeatlas` launcher the fast one?

Hooks and every agent call run `codeatlas ...`. A launcher generated while the entry point was still
`codeatlas.cli:main` imports the whole command line (typer, rich, every sub-command) before it looks at
the arguments, which costs seconds per hook on Windows and skips the fast paths in `codeatlas.entry`.
Reinstalling regenerates the launcher from the current entry point.
"""

from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path


def _entry_text(data: bytes) -> str:
    """The launcher's own source: a script, or the zipped __main__.py appended to a Windows exe."""
    if data[:2] == b"MZ":
        start = data.rfind(b"PK\x03\x04")
        if start < 0:
            return ""
        try:
            with zipfile.ZipFile(io.BytesIO(data[start:])) as archive:
                return archive.read("__main__.py").decode("utf-8", "replace")
        except (zipfile.BadZipFile, KeyError, OSError):
            return ""
    return data[:4096].decode("utf-8", "replace")


def launcher_status(executable: str | None = None) -> tuple[bool | None, str]:
    """(ok, detail): True when the launcher uses the fast entry point, False when it is stale,
    None when it cannot be judged."""
    found = executable or shutil.which("codeatlas")
    if not found:
        return None, "no `codeatlas` on PATH (hooks and agents call `codeatlas`)"
    try:
        text = _entry_text(Path(found).read_bytes())
    except OSError:
        return None, f"cannot read {found}"
    if "codeatlas.entry" in text:
        return True, "fast entry point"
    if "codeatlas.cli" in text:
        return False, (
            f"{found} is out of date and loads the whole command line on every call; "
            "reinstall CODEATLAS (for example `pip install -e .`) to regenerate it"
        )
    return None, f"unrecognised launcher {found}"
