"""Loading and inspecting reference entries from YAML."""

from pathlib import Path

import yaml


def load_references(path: Path) -> list[dict]:
    """Load a YAML file containing a list of reference mappings.

    Raises ``ValueError`` if the file is not a list of mappings.
    """
    with open(path, encoding="utf-8") as f:
        refs = yaml.safe_load(f)

    if not isinstance(refs, list):
        raise ValueError("YAML file must contain a list of references.")  # noqa: TRY004

    for i, ref in enumerate(refs, start=1):
        if not isinstance(ref, dict):
            raise ValueError(f"reference #{i} is not a mapping: {ref!r}")  # noqa: TRY004

    return refs


def text(mapping: dict, key: str) -> str:
    """Return ``mapping[key]`` as a stripped string, or ``""`` if missing or null."""
    value = mapping.get(key)
    return "" if value is None else str(value).strip()


def needs_fetch(ref: dict) -> bool:
    """Return True if a reference has no fields other than ``doi`` and ``tag``."""
    keys = {k for k in ref if text(ref, k)}
    return keys <= {"doi", "tag"}
