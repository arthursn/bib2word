# bib2word

`bib2word` is a command-line tool that converts a YAML bibliography file into a
Microsoft Word-compatible XML bibliography file (suitable for use with Word's
built-in citation manager). It can also automatically fetch reference metadata
from [https://dx.doi.org](https://dx.doi.org) when only a DOI is provided.

## Installation

```bash
pip install bib2word
```

## Usage

```bash
bib2word references.yaml [-o output.xml]
```

If `-o` is omitted, the output file is written next to the input file with a
`.xml` extension. The tool can also be run as `python -m bib2word`.

## Input Format

References are provided as a YAML list. Each entry supports the following fields:

| Field       | Description                                           |
| ----------- | ----------------------------------------------------- |
| `tag`       | Unique citation key (required)                        |
| `type`      | Reference type (see below; default: `JournalArticle`) |
| `title`     | Title of the work                                     |
| `year`      | Publication year                                      |
| `authors`   | List of `{first, last}` name objects                  |
| `journal`   | Journal or container title                            |
| `volume`    | Volume number                                         |
| `issue`     | Issue number                                          |
| `pages`     | Page range (e.g. `100-110`)                           |
| `publisher` | Publisher name                                        |
| `doi`       | DOI (used for auto-fetch if no other fields set)      |
| `url`       | URL                                                   |

### Supported reference types

`JournalArticle`, `Book`, `BookSection`, `ConferenceProceedings`, `Report`,
`Misc`, `Patent`

The `type` field is case-insensitive and also accepts common BibTeX aliases such
as `article`, `inproceedings`, `phdthesis`, etc.

### Example

```yaml
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

# Only a DOI — all metadata will be fetched automatically
- tag: Jones2021
  doi: 10.1038/s41586-021-5678-9
```

## Development

```bash
uv sync            # install the package and dev dependencies
uv run pytest      # run the test suite (no network access needed)
uv run ruff check  # lint
```

Project layout:

| Module                     | Responsibility                                     |
| -------------------------- | -------------------------------------------------- |
| `bib2word/cli.py`          | Argument parsing, user-facing messages, exit codes |
| `bib2word/references.py`   | Loading and validating the YAML input              |
| `bib2word/doi.py`          | Fetching metadata from dx.doi.org                  |
| `bib2word/word_xml.py`     | Building and serializing the Word XML              |

## License

MIT
