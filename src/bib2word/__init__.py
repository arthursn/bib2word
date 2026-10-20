"""Convert YAML bibliographies to Microsoft Word XML bibliographies."""

from .doi import DOIFetchError, fetch_doi_metadata, resolve_reference
from .references import load_references, needs_fetch
from .word_xml import build_sources, ref_to_xml, to_xml_string

__all__ = [
    "DOIFetchError",
    "build_sources",
    "fetch_doi_metadata",
    "load_references",
    "needs_fetch",
    "ref_to_xml",
    "resolve_reference",
    "to_xml_string",
]
