"""
Convert a YAML bibliography file to a Microsoft Word XML bibliography file.

If a reference only has a ``doi`` field, the metadata is fetched automatically
from https://dx.doi.org.

YAML input example
------------------
- tag: Smith2020
  type: JournalArticle
  title: My Article Title
  year: 2020
  authors:
    - first: John
      last: Smith
  journal: Nature
  volume: "123"
  issue: "4"
  pages: "100-110"
  doi: 10.1038/s41586-020-1234-5

- tag: Jones2021
  doi: 10.1038/s41586-021-5678-9   # only doi: details will be fetched

Usage
-----
    bib2word references.yaml -o bibliography.xml
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element, SubElement, tostring

import requests
import yaml

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


def fetch_doi_metadata(doi: str) -> dict:
    """Fetch reference metadata from https://dx.doi.org for a given DOI."""
    url = f"https://dx.doi.org/{doi}"
    headers = {"Accept": "application/vnd.citationstyles.csl+json"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()

    # Parse authors
    authors = []
    for author in data.get("author", []):
        authors.append(
            {
                "first": author.get("given", ""),
                "last": author.get("family", ""),
            }
        )

    # Parse year from issued date-parts [[year, month, day]]
    year = ""
    issued = data.get("issued", {}).get("date-parts", [[]])
    if issued and issued[0]:
        year = str(issued[0][0])

    # Map CSL type to our type
    csl_type = data.get("type", "article-journal")
    type_map = {
        "article-journal": "JournalArticle",
        "book": "Book",
        "chapter": "BookSection",
        "paper-conference": "ConferenceProceedings",
        "report": "Report",
        "thesis": "Report",
        "webpage": "Misc",
    }
    source_type = type_map.get(csl_type, "Misc")

    return {
        "type": source_type,
        "title": data.get("title", ""),
        "year": year,
        "authors": authors,
        "journal": data.get("container-title", ""),
        "volume": str(data.get("volume", "")),
        "issue": str(data.get("issue", "")),
        "pages": data.get("page", ""),
        "publisher": data.get("publisher", ""),
        "doi": doi,
    }


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
        if last := author.get("last", "").strip():
            SubElement(person, b("Last")).text = last
        if first := author.get("first", "").strip():
            SubElement(person, b("First")).text = first


def ref_to_xml(ref: dict) -> Element:
    """Convert a single reference dict to a ``<b:Source>`` XML element."""
    source = Element(b("Source"))

    tag = ref.get("tag") or ref.get("doi", "unknown").replace("/", "_")
    SubElement(source, b("Tag")).text = str(tag)

    raw_type = str(ref.get("type", "JournalArticle"))
    source_type = SOURCE_TYPE_MAP.get(raw_type.lower(), raw_type)
    SubElement(source, b("SourceType")).text = source_type

    if title := ref.get("title", "").strip():
        SubElement(source, b("Title")).text = title

    if year := str(ref.get("year", "")).strip():
        SubElement(source, b("Year")).text = year

    if authors := ref.get("authors"):
        add_authors(source, authors)

    if journal := ref.get("journal", "").strip():
        SubElement(source, b("JournalName")).text = journal

    if volume := str(ref.get("volume", "")).strip():
        SubElement(source, b("Volume")).text = volume

    if issue := str(ref.get("issue", "")).strip():
        SubElement(source, b("Issue")).text = issue

    if pages := str(ref.get("pages", "")).strip():
        SubElement(source, b("Pages")).text = pages

    if publisher := ref.get("publisher", "").strip():
        SubElement(source, b("Publisher")).text = publisher

    if doi := ref.get("doi", "").strip():
        SubElement(source, b("DOI")).text = doi

    if url := ref.get("url", "").strip():
        SubElement(source, b("URL")).text = url

    return source


def main():
    parser = argparse.ArgumentParser(
        description="Convert a YAML bibliography to a Microsoft Word XML bibliography."
    )
    parser.add_argument("input", type=Path, help="Input YAML bibliography file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output XML file (default: same name as input with .xml extension).",
    )
    args = parser.parse_args()

    output: Path = args.output or args.input.with_suffix(".xml")

    with open(args.input) as f:
        refs: list[dict] = yaml.safe_load(f)

    if not isinstance(refs, list):
        print("Error: YAML file must contain a list of references.", file=sys.stderr)
        sys.exit(1)

    sources_el = Element(
        b("Sources"),
        attrib={
            "SelectedStyle": "",
        },
    )

    for i, ref in enumerate(refs):
        # If only a doi is provided, fetch the rest from dx.doi.org
        keys = {k for k, v in ref.items() if v is not None and str(v).strip()}
        if keys <= {"doi", "tag"}:
            doi = ref.get("doi", "").strip()
            if not doi:
                print(
                    f"Warning: reference #{i + 1} has no doi and no other fields, skipping.",
                    file=sys.stderr,
                )
                continue
            print(f"Fetching metadata for DOI: {doi} ...", file=sys.stderr)
            try:
                fetched = fetch_doi_metadata(doi)
            except Exception as e:  # noqa: BLE001
                print(f"Warning: could not fetch DOI {doi!r}: {e}", file=sys.stderr)
                fetched = {}
            # Preserve explicit tag if given
            if "tag" in ref:
                fetched["tag"] = ref["tag"]
            ref = fetched

        sources_el.append(ref_to_xml(ref))

    # Pretty-print the XML
    raw_xml = tostring(sources_el, encoding="unicode", xml_declaration=False)
    pretty_xml = parseString(raw_xml).toprettyxml(indent="  ")

    output.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n' + pretty_xml.partition("\n")[2],
        encoding="utf-8",
    )
    print(f"Written to {output}", file=sys.stderr)
