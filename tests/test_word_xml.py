import xml.etree.ElementTree as ET

import pytest

from bib2word.references import load_references
from bib2word.word_xml import (
    WORD_BIB_NS,
    build_sources,
    ref_to_xml,
    standard_numbers,
    to_xml_string,
)

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
    assert names == ["Tag", "SourceType", "LCID"]


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


def test_extended_fields_in_order():
    ref = {
        "tag": "A",
        "title": "T",
        "short_title": "S",
        "year": 2020,
        "month": 3,
        "day": 15,
        "authors": [{"last": "Smith"}],
        "journal": "J",
        "volume": "1",
        "issue": "2",
        "pages": "3-4",
        "number_volumes": "3",
        "edition": "2",
        "version": "1.0",
        "publisher": "P",
        "isbn": "978-3",
        "doi": "10.1/x",
        "url": "https://example.com",
        "language": "german",
    }
    names = [c.tag.removeprefix(f"{{{WORD_BIB_NS}}}") for c in ref_to_xml(ref)]
    assert names == [
        "Tag", "SourceType", "Title", "ShortTitle", "Year", "Month", "Day",
        "Author", "JournalName", "Volume", "Issue", "Pages", "NumberVolumes",
        "Edition", "Version", "Publisher", "StandardNumber", "DOI", "URL", "LCID",
    ]  # fmt: skip


def test_author_roles():
    ref = {
        "tag": "A",
        "authors": [{"last": "Au"}],
        "editors": [{"last": "Ed"}],
        "inventors": [{"last": "In"}],
        "translators": [{"last": "Tr"}],
    }
    [author_block] = ref_to_xml(ref).findall("b:Author", NS)
    roles = [c.tag.removeprefix(f"{{{WORD_BIB_NS}}}") for c in author_block]
    assert roles == ["Author", "Editor", "Inventor", "Translator"]
    assert (
        author_block.findtext("b:Editor/b:NameList/b:Person/b:Last", namespaces=NS)
        == "Ed"
    )


def test_author_block_omitted_without_people():
    assert ref_to_xml({"tag": "A", "authors": []}).find("b:Author", NS) is None


@pytest.mark.parametrize(
    "ref_type, expected",
    [("phdthesis", "PhD thesis"), ("Thesis", "PhD thesis"), ("article", None)],
)
def test_thesis_type_only_for_thesis_entries(ref_type, expected):
    source = ref_to_xml({"tag": "A", "type": ref_type, "thesis_type": "PhD thesis"})
    assert field(source, "ThesisType") == expected


@pytest.mark.parametrize(
    "ref, expected",
    [
        ({"isbn": "978-3"}, ["978-3"]),  # regression: plain strings were dropped
        ({"issn": ["0028-0836", " 1476-4687 "]}, ["0028-0836", "1476-4687"]),
        ({"standard_number": "NIST 1", "isbn": "978-3"}, ["NIST 1"]),
        ({"standard_number": ["A", "B"]}, ["A", "B"]),
        ({"standard_number": "  ", "isbn": "978-3"}, ["978-3"]),
        ({"isbn": "978-3", "issn": "0028-0836"}, ["978-3"]),  # isbn precedes issn
        ({"isbn": 9783161484100}, ["9783161484100"]),
        ({"issn": [], "isbn": None}, []),
        ({}, []),
    ],
)
def test_standard_numbers(ref, expected):
    assert standard_numbers(ref) == expected


def test_multiple_standard_numbers_emitted():
    source = ref_to_xml({"tag": "A", "issn": ["1", "2"]})
    assert [e.text for e in source.findall("b:StandardNumber", NS)] == ["1", "2"]


@pytest.mark.parametrize(
    "language, expected",
    [(None, "1033"), ("french", "1036"), ("de-AT", "1031"), ("klingon", "1033")],
)
def test_lcid(language, expected):
    assert field(ref_to_xml({"tag": "A", "language": language}), "LCID") == expected


def test_long_values_truncated_to_255_chars():
    source = ref_to_xml(
        {"tag": "A" * 300, "title": "T" * 300, "authors": [{"last": "L" * 300}]}
    )
    assert field(source, "Tag") == "A" * 255
    assert field(source, "Title") == "T" * 255
    assert (
        len(
            source.findtext(
                "b:Author/b:Author/b:NameList/b:Person/b:Last", namespaces=NS
            )
        )
        == 255
    )
