"""Loading and inspecting reference entries from YAML."""

from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq

_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.default_flow_style = False


def load_references(path: Path) -> CommentedSeq:
    """Load a YAML file containing a list of reference mappings.

    Returns a ``CommentedSeq`` of ``CommentedMap`` entries, preserving comments
    and formatting for round-trip writes.
    Raises ``ValueError`` if the file is not a list of mappings.
    """
    with open(path, encoding="utf-8") as f:
        refs = _yaml.load(f)

    if not isinstance(refs, list):
        raise ValueError("YAML file must contain a list of references.")  # noqa: TRY004

    for i, ref in enumerate(refs, start=1):
        if not isinstance(ref, dict):
            raise ValueError(f"reference #{i} is not a mapping: {ref!r}")  # noqa: TRY004

    return refs


def patch_roundtrip_entry(rt_entry, fetched: dict) -> None:
    """Replace all keys in ``rt_entry`` (except ``tag``) with values from ``fetched``.

    Operates in-place on the ruamel.yaml ``CommentedMap`` so that surrounding
    comments are preserved.
    """
    tag = rt_entry.get("tag")
    # Remove all existing keys
    for key in list(rt_entry.keys()):
        del rt_entry[key]
    # Re-insert from fetched data
    for key, value in fetched.items():
        rt_entry[key] = value
    # Restore tag as first key
    if tag is not None:
        rt_entry.insert(0, "tag", tag)


def save_roundtrip(path: Path, refs: CommentedSeq) -> None:
    """Write ``refs`` back to ``path`` using ruamel.yaml (preserves comments)."""
    with open(path, "w", encoding="utf-8") as f:
        _yaml.dump(refs, f)


def text(mapping: dict, key: str) -> str:
    """Return ``mapping[key]`` as a stripped string, or ``""`` if missing or null."""
    value = mapping.get(key)
    return "" if value is None else str(value).strip()


def needs_fetch(ref: dict) -> bool:
    """Return True if a reference has no fields other than ``doi`` and ``tag``."""
    keys = {k for k in ref if text(ref, k)}
    return keys <= {"doi", "tag"}
