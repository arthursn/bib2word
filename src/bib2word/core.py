"""
Convert a YAML bibliography file to a Microsoft Word XML bibliography file.

If a reference only has a ``doi`` field, the metadata is fetched automatically
from https://dx.doi.org.

YAML input example
------------------
- tag: Smith2020
  type: JournalArticle
  title: My Article Title
  short_title: My Article
  year: 2020
  month: "3"
  day: "15"
  authors:
    - first: John
      last: Smith
  editors:
    - first: Jane
      last: Doe
  journal: Nature
  volume: "123"
  issue: "4"
  pages: "100-110"
  edition: "2"
  version: "1.0"
  number_volumes: "3"
  isbn: "978-3-16-148410-0"
  doi: 10.1038/s41586-020-1234-5
  url: https://example.com
  language: english
  thesis_type: PhD thesis

- tag: Jones2021
  doi: 10.1038/s41586-021-5678-9   # only doi: details will be fetched

Supported author-role keys
--------------------------
  authors, editors, inventors, translators

  Each entry is a list of dicts with ``first`` and/or ``last`` keys.

Supported language values
-------------------------
  BibTeX language names (e.g. ``english``, ``french``, ``german``) and
  BCP-47 codes (e.g. ``en``, ``fr-FR``, ``de-AT``) are both accepted.
  Defaults to English (LCID 1033) when omitted.

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
    # Misc / online
    "booklet": "Misc",
    "unpublished": "Misc",
    "misc": "Misc",
    "online": "Misc",
    "webpage": "Misc",
    # Patent
    "patent": "Patent",
}

# BibTeX / BCP-47 language identifiers → Windows LCID strings.
# Source: ECMA-376 + bibtex2wordbid.sh
_LANG_LCID: dict[str, str] = {
    # Arabic
    **dict.fromkeys(
        [
            "arabic",
            "aeb",
            "ar",
            "ar-iq",
            "ar-jo",
            "ar-lb",
            "ar-mr",
            "ar-ps",
            "ar-sy",
            "ar-ye",
            "arq",
            "ary",
            "arz",
            "ayl",
        ],
        "1025",
    ),
    "bulgarian": "1026",
    "bg": "1026",
    "catalan": "1027",
    "ca": "1027",
    "czech": "1029",
    "cz": "1029",
    "danish": "1030",
    "da": "1030",
    **dict.fromkeys(
        [
            "german",
            "naustrian",
            "ngerman",
            "nswissgerman",
            "swissgerman",
            "de",
            "de-at",
            "de-ch",
            "de-de",
            "de-latf",
            "de-latf-at",
            "de-latf-ch",
            "de-latf-de",
        ],
        "1031",
    ),
    "greek": "1032",
    "polutonikogreek": "1032",
    "el": "1032",
    **dict.fromkeys(
        [
            "english",
            "american",
            "australian",
            "british",
            "canadian",
            "newzealand",
            "en",
            "en-au",
            "en-ca",
            "en-gb",
            "en-nz",
            "en-us",
        ],
        "1033",
    ),
    **dict.fromkeys(["spanish", "spanishmx", "es", "es-es", "es-mx"], "1034"),
    "finnish": "1035",
    "fi": "1035",
    **dict.fromkeys(["french", "acadien", "fr", "fr-ca", "fr-ch", "fr-fr"], "1036"),
    "hebrew": "1037",
    "he": "1037",
    "hungarian": "1038",
    "magyar": "1038",
    "hu": "1038",
    "icelandic": "1039",
    "is": "1039",
    "italian": "1040",
    "it": "1040",
    "japanese": "1041",
    "ja": "1041",
    "korean": "1042",
    "ko": "1042",
    "dutch": "1043",
    "nl": "1043",
    **dict.fromkeys(["norwegian", "norsk", "nynorsk", "nb"], "1044"),
    "polish": "1045",
    "pl": "1045",
    **dict.fromkeys(
        ["portuguese", "brazil", "portuges", "pt", "pt-br", "pt-pt"], "1046"
    ),
    "romansh": "1047",
    "rm": "1047",
    "romanian": "1048",
    "ro": "1048",
    "russian": "1049",
    "ru": "1049",
    "croatian": "1050",
    "hr": "1050",
    "slovak": "1051",
    "sk": "1051",
    "albanian": "1052",
    "sq": "1052",
    "swedish": "1053",
    "sv": "1053",
    "thai": "1054",
    "th": "1054",
    "turkish": "1055",
    "tr": "1055",
    "urdu": "1056",
    "ur": "1056",
    **dict.fromkeys(["malay", "bahasa", "bahasam", "id"], "1057"),
    "ukrainian": "1058",
    "uk": "1058",
    "belarusian": "1059",
    "be": "1059",
    "slovenian": "1060",
    "slovene": "1060",
    "sl": "1060",
    "estonian": "1061",
    "et": "1061",
    "latvian": "1062",
    "lv": "1062",
    "lithuanian": "1063",
    "lt": "1063",
    "farsi": "1065",
    "persian": "1065",
    "vietnamese": "1066",
    "vi": "1066",
    "armenian": "1067",
    "hy": "1067",
    "basque": "1069",
    "eu": "1069",
    "macedonian": "1071",
    "mk": "1071",
    "afrikaans": "1078",
    "af": "1078",
    "georgian": "1079",
    "ka": "1079",
    "hindi": "1081",
    "hi": "1081",
    **dict.fromkeys(["sami", "samin", "se"], "1083"),
    **dict.fromkeys(["gaelic", "irish", "scottish", "gd"], "1084"),
    "turkmen": "1090",
    "tk": "1090",
    "bengali": "1093",
    "bn": "1093",
    "tamil": "1097",
    "ta": "1097",
    "telugu": "1098",
    "te": "1098",
    "malayalam": "1100",
    "ml": "1100",
    "marathi": "1102",
    "mr": "1102",
    "sanskrit": "1103",
    "sa": "1103",
    "mongolian": "1104",
    "mn": "1104",
    "tibetan": "1105",
    "bo": "1105",
    "welsh": "1106",
    "cy": "1106",
    "khmer": "1107",
    "km": "1107",
    "lao": "1108",
    "lo": "1108",
    "galician": "1110",
    "gl": "1110",
    "syriac": "1114",
    "syr": "1114",
}

_STANDARD_NUMBER_KEYS = {"isan", "isbn", "ismn", "isrn", "issn", "iswc"}
_THESIS_TYPES = {"thesis", "mastersthesis", "phdthesis"}
_WORD_FIELD_MAX = 255


def _trunc(value: str) -> str:
    """Truncate a string to the Word bibliography field limit (255 chars)."""
    return value[:_WORD_FIELD_MAX]


def lang_to_lcid(lang: str) -> str:
    """Return the Windows LCID string for a BibTeX/BCP-47 language identifier.

    Falls back to ``"1033"`` (English) for unknown values.
    """
    return _LANG_LCID.get(lang.strip().lower(), "1033")


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

    # Map CSL type to our YAML type key so SOURCE_TYPE_MAP resolves it
    csl_type = data.get("type", "article-journal")
    csl_type_map = {
        "article-journal": "article",
        "book": "book",
        "chapter": "inbook",
        "paper-conference": "inproceedings",
        "report": "report",
        "thesis": "thesis",
        "webpage": "online",
        "periodical": "periodical",
    }
    yaml_type = csl_type_map.get(csl_type, "misc")
    source_type = SOURCE_TYPE_MAP.get(yaml_type, "Misc")

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
        "isbn": data.get("ISBN", ""),
        "issn": data.get("ISSN", ""),
        "doi": doi,
        "url": data.get("URL", ""),
    }


def b(tag: str) -> str:
    """Return a qualified tag name in the Word bibliography namespace."""
    return f"{{{WORD_BIB_NS}}}{tag}"


def _add_name_list(role_el: Element, role_tag: str, people: list[dict]) -> None:
    """Append a ``<b:{role_tag}><b:NameList>…`` block to *role_el*."""
    inner = SubElement(role_el, b(role_tag))
    name_list = SubElement(inner, b("NameList"))
    for person_dict in people:
        person = SubElement(name_list, b("Person"))
        if last := person_dict.get("last", "").strip():
            SubElement(person, b("Last")).text = _trunc(last)
        if first := person_dict.get("first", "").strip():
            SubElement(person, b("First")).text = _trunc(first)


def add_authors(source_el: Element, ref: dict) -> None:
    """Add an ``<b:Author>`` block with all author roles to *source_el*.

    Reads ``authors``, ``editors``, ``inventors``, and ``translators`` from
    *ref*.  The block is omitted entirely when none of those keys are present.
    """
    roles = [
        ("authors", "Author"),
        ("editors", "Editor"),
        ("inventors", "Inventor"),
        ("translators", "Translator"),
    ]
    present = [(key, tag) for key, tag in roles if ref.get(key)]
    if not present:
        return

    author_outer = SubElement(source_el, b("Author"))
    for key, tag in present:
        _add_name_list(author_outer, tag, ref[key])


def ref_to_xml(ref: dict) -> Element:
    """Convert a single reference dict to a ``<b:Source>`` XML element."""
    source = Element(b("Source"))

    tag = ref.get("tag") or ref.get("doi", "unknown").replace("/", "_")
    SubElement(source, b("Tag")).text = _trunc(str(tag))

    raw_type = str(ref.get("type", "JournalArticle"))
    source_type = SOURCE_TYPE_MAP.get(raw_type.lower(), raw_type)
    SubElement(source, b("SourceType")).text = source_type

    if title := ref.get("title", "").strip():
        SubElement(source, b("Title")).text = _trunc(title)

    if short_title := ref.get("short_title", "").strip():
        SubElement(source, b("ShortTitle")).text = _trunc(short_title)

    # Date fields
    if year := str(ref.get("year", "")).strip():
        SubElement(source, b("Year")).text = _trunc(year)
    if month := str(ref.get("month", "")).strip():
        SubElement(source, b("Month")).text = _trunc(month)
    if day := str(ref.get("day", "")).strip():
        SubElement(source, b("Day")).text = _trunc(day)

    # All author roles
    add_authors(source, ref)

    if journal := ref.get("journal", "").strip():
        SubElement(source, b("JournalName")).text = _trunc(journal)

    if volume := str(ref.get("volume", "")).strip():
        SubElement(source, b("Volume")).text = _trunc(volume)

    if issue := str(ref.get("issue", "")).strip():
        SubElement(source, b("Issue")).text = _trunc(issue)

    if pages := str(ref.get("pages", "")).strip():
        SubElement(source, b("Pages")).text = _trunc(pages)

    if number_volumes := str(ref.get("number_volumes", "")).strip():
        SubElement(source, b("NumberVolumes")).text = _trunc(number_volumes)

    if edition := str(ref.get("edition", "")).strip():
        SubElement(source, b("Edition")).text = _trunc(edition)

    if version := str(ref.get("version", "")).strip():
        SubElement(source, b("Version")).text = _trunc(version)

    if publisher := ref.get("publisher", "").strip():
        SubElement(source, b("Publisher")).text = _trunc(publisher)

    # Thesis type (only meaningful for thesis entry types)
    if (raw_type.lower() in _THESIS_TYPES) and (
        thesis_type := ref.get("thesis_type", "").strip()
    ):
        SubElement(source, b("ThesisType")).text = _trunc(thesis_type)

    # Standard numbers: prefer explicit standard_number, then isbn/issn/etc.
    std_num = ref.get("standard_number", "").strip()
    std_nums = []
    if not std_num:
        for key in _STANDARD_NUMBER_KEYS:
            if val := ref.get(key, ""):
                if isinstance(val, str):
                    std_num = std_num.strip()
                elif isinstance(val, list):
                    for v in val:
                        if std_num := v.strip():
                            std_nums.append(std_num)
                    std_num = None
                break
    if std_num:
        SubElement(source, b("StandardNumber")).text = _trunc(std_num)
    if std_nums:
        for std_num in std_nums:
            SubElement(source, b("StandardNumber")).text = _trunc(std_num)

    if doi := ref.get("doi", "").strip():
        SubElement(source, b("DOI")).text = _trunc(doi)

    if url := ref.get("url", "").strip():
        SubElement(source, b("URL")).text = _trunc(url)

    # Language / LCID — default to English (1033) when not provided
    lang = ref.get("language", "").strip()
    SubElement(source, b("LCID")).text = lang_to_lcid(lang) if lang else "1033"

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
