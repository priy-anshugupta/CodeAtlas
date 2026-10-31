"""Do not send unwritten narrative scaffolding to an agent."""

from codeatlas.writers.agents_md import NARRATIVE_PLACEHOLDER as BRIEF_PLACEHOLDER
from codeatlas.writers.modules_md import NARRATIVE_PLACEHOLDER as MODULE_PLACEHOLDER


def real_narrative(text: str) -> str:
    if text.strip() in {BRIEF_PLACEHOLDER, MODULE_PLACEHOLDER, "TODO", "_TODO_"}:
        return ""
    return text


def without_placeholders(text: str) -> str:
    return text.replace(BRIEF_PLACEHOLDER, "").replace(MODULE_PLACEHOLDER, "")
