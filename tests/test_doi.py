import pytest
import requests

from bib2word.doi import DOIFetchError, fetch_doi_metadata, resolve_reference
from tests.conftest import FakeResponse

CSL_PAYLOAD = {
    "type": "article-journal",
    "title": "A Great Paper",
    "author": [
        {"given": "Jane", "family": "Doe"},
        {"given": "Richard", "family": "Roe"},
    ],
    "issued": {"date-parts": [[2021, 5, 3]]},
    "container-title": "Nature",
    "volume": 590,
    "issue": "7845",
    "page": "100-110",
    "publisher": "Springer",
}


def test_fetch_parses_csl_json(fake_get):
    fake_get["10.1/x"] = FakeResponse(CSL_PAYLOAD)

    assert fetch_doi_metadata("10.1/x") == {
        "type": "JournalArticle",
        "title": "A Great Paper",
        "year": "2021",
        "authors": [
            {"first": "Jane", "last": "Doe"},
            {"first": "Richard", "last": "Roe"},
        ],
        "journal": "Nature",
        "volume": "590",
        "issue": "7845",
        "pages": "100-110",
        "publisher": "Springer",
        "doi": "10.1/x",
    }


def test_fetch_handles_minimal_payload(fake_get):
    fake_get["10.1/x"] = FakeResponse({"type": "dataset"})

    meta = fetch_doi_metadata("10.1/x")

    assert meta["type"] == "Misc"
    assert meta["year"] == ""
    assert meta["authors"] == []
    assert meta["volume"] == ""
    assert meta["journal"] == ""


def test_fetch_handles_list_valued_fields(fake_get):
    fake_get["10.1/x"] = FakeResponse(
        {"title": ["Main Title", "Alt"], "container-title": []}
    )

    meta = fetch_doi_metadata("10.1/x")

    assert meta["title"] == "Main Title"
    assert meta["journal"] == ""


@pytest.mark.parametrize(
    "csl_type, expected",
    [
        ("article-journal", "JournalArticle"),
        ("journal-article", "JournalArticle"),  # Crossref name, as returned by doi.org
        ("book-chapter", "BookSection"),
        ("proceedings-article", "ConferenceProceedings"),
        ("dissertation", "Report"),
        ("dataset", "Misc"),
    ],
)
def test_fetch_maps_csl_and_crossref_types(fake_get, csl_type, expected):
    fake_get["10.1/x"] = FakeResponse({"type": csl_type})
    assert fetch_doi_metadata("10.1/x")["type"] == expected


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(status_code=404),
        FakeResponse(json_error=True),
        requests.ConnectionError("no route to host"),
    ],
    ids=["http-error", "bad-json", "connection-error"],
)
def test_fetch_errors_raise_doi_fetch_error(fake_get, response):
    fake_get["10.1/x"] = response
    with pytest.raises(DOIFetchError):
        fetch_doi_metadata("10.1/x")


def test_resolve_reference_preserves_tag(fake_get):
    fake_get["10.1/x"] = FakeResponse(CSL_PAYLOAD)

    ref = resolve_reference({"tag": "Doe2021", "doi": " 10.1/x "})

    assert ref["tag"] == "Doe2021"
    assert ref["title"] == "A Great Paper"
    assert fake_get.calls == ["10.1/x"]


def test_resolve_reference_without_tag(fake_get):
    fake_get["10.1/x"] = FakeResponse(CSL_PAYLOAD)
    assert "tag" not in resolve_reference({"doi": "10.1/x"})
