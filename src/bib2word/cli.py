"""Command-line interface for bib2word."""

import argparse
import sys
from pathlib import Path

import yaml

from .doi import DOIFetchError, resolve_reference
from .references import load_references, needs_fetch, text
from .word_xml import build_sources, to_xml_string


def _warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="bib2word",
        description="Convert a YAML bibliography to a Microsoft Word XML bibliography.",
    )
    parser.add_argument("input", type=Path, help="Input YAML bibliography file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output XML file (default: same name as input with .xml extension).",
    )
    args = parser.parse_args(argv)

    output: Path = args.output or args.input.with_suffix(".xml")

    try:
        refs = load_references(args.input)
    except (OSError, yaml.YAMLError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    resolved: list[dict] = []
    for i, ref in enumerate(refs, start=1):
        # If only a doi is provided, fetch the rest from dx.doi.org
        if needs_fetch(ref):
            doi = text(ref, "doi")
            if not doi:
                _warn(f"reference #{i} has no doi and no other fields, skipping.")
                continue
            print(f"Fetching metadata for DOI: {doi} ...", file=sys.stderr)
            try:
                ref = resolve_reference(ref)
            except DOIFetchError as e:
                _warn(f"could not fetch DOI {doi!r}: {e}")
        resolved.append(ref)

    output.write_text(to_xml_string(build_sources(resolved)), encoding="utf-8")
    print(f"Written to {output}", file=sys.stderr)
