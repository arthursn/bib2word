"""Fetching reference metadata from https://dx.doi.org."""

import requests

# Map from CSL types to Word XML SourceType values. dx.doi.org often returns
# Crossref type names (e.g. "journal-article") instead of standard CSL ones.
CSL_TYPE_MAP: dict[str, str] = {
    "article-journal": "JournalArticle",
    "journal-article": "JournalArticle",
    "book": "Book",
    "monograph": "Book",
    "edited-book": "Book",
    "chapter": "BookSection",
    "book-chapter": "BookSection",
    "paper-conference": "ConferenceProceedings",
    "proceedings-article": "ConferenceProceedings",
    "report": "Report",
    "thesis": "Report",
    "dissertation": "Report",
    "webpage": "Misc",
    "periodical": "ArticleInAPeriodical",
}


class DOIFetchError(Exception):
    """Raised when metadata for a DOI cannot be fetched or parsed."""


def _first(value) -> str:
    """CSL fields like ``container-title`` may be a string or a list of strings."""
    if isinstance(value, list):
        value = value[0] if value else ""
    return "" if value is None else str(value)


def fetch_doi_metadata(doi: str) -> dict:
    """Fetch reference metadata from https://dx.doi.org for a given DOI."""
    url = f"https://dx.doi.org/{doi}"
    headers = {"Accept": "application/vnd.citationstyles.csl+json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        raise DOIFetchError(str(e)) from e

    # Parse authors
    authors = [
        {"first": author.get("given", ""), "last": author.get("family", "")}
        for author in data.get("author", [])
    ]

    # Parse year from issued date-parts [[year, month, day]]
    year = ""
    issued = data.get("issued", {}).get("date-parts", [[]])
    if issued and issued[0]:
        year = str(issued[0][0])

    csl_type = data.get("type", "article-journal")

    return {
        "type": CSL_TYPE_MAP.get(csl_type, "Misc"),
        "title": _first(data.get("title")),
        "year": year,
        "authors": authors,
        "journal": _first(data.get("container-title")),
        "volume": _first(data.get("volume")),
        "issue": _first(data.get("issue")),
        "pages": _first(data.get("page")),
        "publisher": _first(data.get("publisher")),
        "isbn": data.get("ISBN", ""),
        "issn": data.get("ISSN", ""),
        "doi": doi,
        "url": _first(data.get("URL")),
    }


def resolve_reference(ref: dict) -> dict:
    """Return ``ref`` filled in with metadata fetched from its DOI.

    An explicit ``tag`` is preserved. Raises ``DOIFetchError`` on failure.
    """
    fetched = fetch_doi_metadata(str(ref["doi"]).strip())
    if ref.get("tag") is not None:
        fetched["tag"] = ref["tag"]
    return fetched
