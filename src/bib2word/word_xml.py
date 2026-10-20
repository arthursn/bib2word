"""Building Microsoft Word XML bibliography documents."""

import copy
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement

from .references import text

WORD_BIB_NS = "http://schemas.openxmlformats.org/officeDocument/2006/bibliography"

# Register the namespace prefix so ElementTree emits xmlns:b="..." instead of
# expanding the URI inline on every tag, which Word cannot parse.
ET.register_namespace("b", WORD_BIB_NS)

# Map from our YAML types to Word XML SourceType values
SOURCE_TYPE_MAP: dict[str, str] = {
    "article": "JournalArticle",
    "journalarticle": "JournalArticle",
    "book": "Book",
    "booklet": "Book",
    "inbook": "BookSection",
    "incollection": "BookSection",
    "inproceedings": "ConferenceProceedings",
    "conference": "ConferenceProceedings",
    "proceedings": "ConferenceProceedings",
    "techreport": "Report",
    "report": "Report",
    "thesis": "Report",
    "mastersthesis": "Report",
    "phdthesis": "Report",
    "misc": "Misc",
    "online": "Misc",
    "webpage": "Misc",
    "patent": "Patent",
}

# YAML field -> Word XML element, in output order (after Tag/SourceType/Title/Year/Author)
_SIMPLE_FIELDS: list[tuple[str, str]] = [
    ("journal", "JournalName"),
    ("volume", "Volume"),
    ("issue", "Issue"),
    ("pages", "Pages"),
    ("publisher", "Publisher"),
    ("doi", "DOI"),
    ("url", "URL"),
]


def b(tag: str) -> str:
    """Return a qualified tag name in the Word bibliography namespace."""
    return f"{{{WORD_BIB_NS}}}{tag}"


def add_authors(source_el: Element, authors: list[dict]) -> None:
    """Add an ``<b:Author>`` block to a source element."""
    author_outer = SubElement(source_el, b("Author"))
    author_inner = SubElement(author_outer, b("Author"))
    name_list = SubElement(author_inner, b("NameList"))
    for author in authors:
        person = SubElement(name_list, b("Person"))
        if last := text(author, "last"):
            SubElement(person, b("Last")).text = last
        if first := text(author, "first"):
            SubElement(person, b("First")).text = first


def ref_to_xml(ref: dict) -> Element:
    """Convert a single reference dict to a ``<b:Source>`` XML element."""
    source = Element(b("Source"))

    tag = text(ref, "tag") or text(ref, "doi").replace("/", "_") or "unknown"
    SubElement(source, b("Tag")).text = tag

    raw_type = text(ref, "type") or "JournalArticle"
    SubElement(source, b("SourceType")).text = SOURCE_TYPE_MAP.get(
        raw_type.lower(), raw_type
    )

    if title := text(ref, "title"):
        SubElement(source, b("Title")).text = title

    if year := text(ref, "year"):
        SubElement(source, b("Year")).text = year

    if authors := ref.get("authors"):
        add_authors(source, authors)

    for key, element in _SIMPLE_FIELDS:
        if value := text(ref, key):
            SubElement(source, b(element)).text = value

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
