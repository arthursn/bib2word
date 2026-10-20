import xml.etree.ElementTree as ET

import pytest

from bib2word.references import load_references
from bib2word.word_xml import WORD_BIB_NS, build_sources, ref_to_xml, to_xml_string

NS = {"b": WORD_BIB_NS}


def field(source: ET.Element, name: str) -> str | None:
    return source.findtext(f"b:{name}", namespaces=NS)


def test_full_document_matches_expected(data_dir):
    refs = load_references(data_dir / "smith2020.yaml")
    xml = to_xml_string(build_sources(refs))
    assert xml == (data_dir / "smith2020.xml").read_text(encoding="utf-8")


def test_root_uses_b_prefix_and_selected_style():
    xml = to_xml_string(build_sources([]))
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<b:Sources ')
    assert f'xmlns:b="{WORD_BIB_NS}"' in xml
    assert 'SelectedStyle=""' in xml
    assert "ns0:" not in xml


def test_to_xml_string_does_not_mutate_input():
    sources = build_sources([{"tag": "A", "title": "T"}])
    before = ET.tostring(sources)
    to_xml_string(sources)
    assert ET.tostring(sources) == before


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("article", "JournalArticle"),
        ("Article", "JournalArticle"),
        ("PHDTHESIS", "Report"),
        ("inproceedings", "ConferenceProceedings"),
        ("Book", "Book"),
        ("ArtWork", "ArtWork"),  # unknown types pass through unchanged
    ],
)
def test_source_type_mapping(raw, expected):
    assert field(ref_to_xml({"tag": "A", "type": raw}), "SourceType") == expected


@pytest.mark.parametrize("ref", [{"tag": "A"}, {"tag": "A", "type": None}])
def test_source_type_defaults_to_journal_article(ref):
    assert field(ref_to_xml(ref), "SourceType") == "JournalArticle"


@pytest.mark.parametrize(
    "ref, expected",
    [
        ({"tag": "Smith2020", "doi": "10.1/x"}, "Smith2020"),
        ({"doi": "10.1038/abc"}, "10.1038_abc"),
        ({"doi": None}, "unknown"),
        ({}, "unknown"),
    ],
)
def test_tag_fallback(ref, expected):
    assert field(ref_to_xml(ref), "Tag") == expected


def test_null_and_blank_fields_are_omitted():
    ref = {
        "tag": "A",
        "title": None,
        "journal": "   ",
        "publisher": None,
        "doi": None,
        "url": "",
    }
    source = ref_to_xml(ref)
    names = [child.tag.removeprefix(f"{{{WORD_BIB_NS}}}") for child in source]
    assert names == ["Tag", "SourceType"]


def test_numeric_fields_are_stringified():
    source = ref_to_xml({"tag": "A", "year": 2020, "volume": 12, "issue": 3})
    assert field(source, "Year") == "2020"
    assert field(source, "Volume") == "12"
    assert field(source, "Issue") == "3"


def test_authors():
    authors = [
        {"first": "John", "last": "Smith"},
        {"last": "Doe", "first": None},
    ]
    source = ref_to_xml({"tag": "A", "authors": authors})
    people = source.findall("b:Author/b:Author/b:NameList/b:Person", NS)
    assert [(field(p, "First"), field(p, "Last")) for p in people] == [
        ("John", "Smith"),
        (None, "Doe"),
    ]


def test_url_and_publisher():
    source = ref_to_xml({"tag": "A", "publisher": "ACME", "url": "https://example.com"})
    assert field(source, "Publisher") == "ACME"
    assert field(source, "URL") == "https://example.com"
