"""Building Microsoft Word XML bibliography documents."""

import copy
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement

from .languages import lang_to_lcid
from .references import text

WORD_BIB_NS = "http://schemas.openxmlformats.org/officeDocument/2006/bibliography"

# Register the namespace prefix so ElementTree emits xmlns:b="..." instead of
# expanding the URI inline on every tag, which Word cannot parse.
ET.register_namespace("b", WORD_BIB_NS)

# Map from our YAML / BibTeX types to Word XML SourceType values.
# Aligned with the full type list from bibtex2wordbid.sh.
SOURCE_TYPE_MAP: dict[str, str] = {
    # Journal / periodical
    "article": "JournalArticle",
    "journalarticle": "JournalArticle",
    "periodical": "ArticleInAPeriodical",
    "suppperiodical": "ArticleInAPeriodical",
    # Book
    "book": "Book",
    "suppbook": "Book",
    "bookinbook": "Book",
    "mvbook": "Book",
    # Book section / collection
    "inbook": "BookSection",
    "incollection": "BookSection",
    "suppcollection": "BookSection",
    "collection": "BookSection",
    "mvcollection": "BookSection",
    # Conference / proceedings
    "inproceedings": "ConferenceProceedings",
    "conference": "ConferenceProceedings",
    "proceedings": "ConferenceProceedings",
    "mvproceedings": "ConferenceProceedings",
    # Reference works
    "inreference": "Report",
    "reference": "Report",
    "mvreference": "Report",
    # Reports / theses
    "manual": "Report",
    "techreport": "Report",
    "report": "Report",
    "thesis": "Report",
    "mastersthesis": "Report",
    "phdthesis": "Report",
    # Online
    "online": "InternetSite",
    "webpage": "InternetSite",
    "website": "InternetSite",
    "www": "InternetSite",
    "internetsite": "InternetSite",
    # Misc
    "booklet": "Misc",
    "unpublished": "Misc",
    "misc": "Misc",
    # Patent
    "patent": "Patent",
}

# Word limits bibliography text fields to 255 characters.
_WORD_FIELD_MAX = 255

# YAML field -> Word XML element, for fields written before the author block
_FIELDS_BEFORE_AUTHORS: list[tuple[str, str]] = [
    ("title", "Title"),
    ("short_title", "ShortTitle"),
    ("year", "Year"),
    ("month", "Month"),
    ("day", "Day"),
]

# YAML field -> Word XML element, for fields written after the author block
_FIELDS_AFTER_AUTHORS: list[tuple[str, str]] = [
    ("journal", "JournalName"),
    ("volume", "Volume"),
    ("issue", "Issue"),
    ("pages", "Pages"),
    ("number_volumes", "NumberVolumes"),
    ("edition", "Edition"),
    ("version", "Version"),
    ("publisher", "Publisher"),
]

# YAML author-role key -> Word XML role element
_AUTHOR_ROLES: list[tuple[str, str]] = [
    ("authors", "Author"),
    ("editors", "Editor"),
    ("inventors", "Inventor"),
    ("translators", "Translator"),
]

# Keys that may hold a standard number, in order of precedence
_STANDARD_NUMBER_KEYS = (
    "standard_number",
    "isbn",
    "issn",
    "ismn",
    "isan",
    "isrn",
    "iswc",
)

_THESIS_TYPES = {"thesis", "mastersthesis", "phdthesis"}


def b(tag: str) -> str:
    """Return a qualified tag name in the Word bibliography namespace."""
    return f"{{{WORD_BIB_NS}}}{tag}"


def _trunc(value: str) -> str:
    """Truncate a string to the Word bibliography field limit (255 chars)."""
    return value[:_WORD_FIELD_MAX]


def _add_fields(source: Element, ref: dict, fields: list[tuple[str, str]]) -> None:
    """Append a text element for each non-blank ``ref`` field in *fields*."""
    for key, element in fields:
        if value := text(ref, key):
            SubElement(source, b(element)).text = _trunc(value)


def _add_name_list(role_el: Element, role_tag: str, people: list[dict]) -> None:
    """Append a ``<b:{role_tag}><b:NameList>…`` block to *role_el*."""
    inner = SubElement(role_el, b(role_tag))
    name_list = SubElement(inner, b("NameList"))
    for person_dict in people:
        person = SubElement(name_list, b("Person"))
        if last := text(person_dict, "last"):
            SubElement(person, b("Last")).text = _trunc(last)
        if first := text(person_dict, "first"):
            SubElement(person, b("First")).text = _trunc(first)


def add_authors(source_el: Element, ref: dict) -> None:
    """Add an ``<b:Author>`` block with all author roles to *source_el*.

    Reads ``authors``, ``editors``, ``inventors``, and ``translators`` from
    *ref*.  The block is omitted entirely when none of those keys are present.
    """
    present = [(key, tag) for key, tag in _AUTHOR_ROLES if ref.get(key)]
    if not present:
        return

    author_outer = SubElement(source_el, b("Author"))
    for key, tag in present:
        _add_name_list(author_outer, tag, ref[key])


def standard_numbers(ref: dict) -> list[str]:
    """Return the standard numbers for *ref*.

    ``standard_number`` takes precedence, then isbn/issn/etc. The first key
    with a value wins; values may be a single string or a list of strings.
    """
    for key in _STANDARD_NUMBER_KEYS:
        value = ref.get(key)
        values = value if isinstance(value, list) else [value]
        if numbers := [s for v in values if v is not None and (s := str(v).strip())]:
            return numbers
    return []


def ref_to_xml(ref: dict) -> Element:
    """Convert a single reference dict to a ``<b:Source>`` XML element."""
    source = Element(b("Source"))

    tag = text(ref, "tag") or text(ref, "doi").replace("/", "_") or "unknown"
    SubElement(source, b("Tag")).text = _trunc(tag)

    raw_type = text(ref, "type") or "JournalArticle"
    SubElement(source, b("SourceType")).text = SOURCE_TYPE_MAP.get(
        raw_type.lower(), raw_type
    )

    _add_fields(source, ref, _FIELDS_BEFORE_AUTHORS)
    add_authors(source, ref)
    _add_fields(source, ref, _FIELDS_AFTER_AUTHORS)

    # Thesis type (only meaningful for thesis entry types)
    if raw_type.lower() in _THESIS_TYPES:
        _add_fields(source, ref, [("thesis_type", "ThesisType")])

    for number in standard_numbers(ref):
        SubElement(source, b("StandardNumber")).text = _trunc(number)

    _add_fields(source, ref, [("doi", "DOI"), ("url", "URL")])

    # Language / LCID — default to English (1033) when not provided
    SubElement(source, b("LCID")).text = lang_to_lcid(text(ref, "language"))

    return source


def build_sources(refs: list[dict]) -> Element:
    """Build the root ``<b:Sources>`` element from a list of reference dicts."""
    sources = Element(b("Sources"), attrib={"SelectedStyle": ""})
    for ref in refs:
        sources.append(ref_to_xml(ref))
    return sources


def to_xml_string(sources: Element) -> str:
    """Serialize a ``<b:Sources>`` element as a pretty-printed XML document."""
    sources = copy.deepcopy(sources)
    ET.indent(sources, space="  ")
    body = ET.tostring(sources, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{body}\n'
