# bib2word

`bib2word` is a command-line tool that converts a YAML bibliography file into a
Microsoft Word-compatible XML bibliography file (suitable for use with Word's
built-in citation manager). It can also automatically fetch reference metadata
from [https://dx.doi.org](https://dx.doi.org) when only a DOI is provided.

> **Acknowledgement** — The reference-type mapping, LCID language table, and
> field-handling logic in this tool were informed by
> [bibtex2wordbib](https://github.com/msdm/bibtex2wordbib) by
> [msdm](https://github.com/msdm), which implements the same conversion as a
> bash script based on the
> [ECMA-376 standard](https://www.ecma-international.org/publications/standards/Ecma-376.htm).

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

### Core fields

| Field         | Description                                                       |
| ------------- | ----------------------------------------------------------------- |
| `tag`         | Unique citation key (required)                                    |
| `type`        | Reference type (see below; default: `JournalArticle`)             |
| `title`       | Title of the work                                                 |
| `short_title` | Abbreviated title                                                 |
| `year`        | Publication year                                                  |
| `month`       | Publication month                                                 |
| `day`         | Publication day                                                   |
| `publisher`   | Publisher name                                                    |
| `doi`         | DOI (used for auto-fetch when it is the only field set)           |
| `url`         | URL                                                               |
| `language`    | Language (BibTeX name or BCP-47 code, e.g. `english`, `fr`, `de`) |

### Author roles

Each role is a list of `{first, last}` name objects.

| Field         | Word role  |
| ------------- | ---------- |
| `authors`     | Author     |
| `editors`     | Editor     |
| `inventors`   | Inventor   |
| `translators` | Translator |

### Periodical / book fields

| Field            | Description                 |
| ---------------- | --------------------------- |
| `journal`        | Journal or container title  |
| `volume`         | Volume number               |
| `issue`          | Issue number                |
| `pages`          | Page range (e.g. `100-110`) |
| `edition`        | Edition                     |
| `version`        | Version                     |
| `number_volumes` | Number of volumes           |

### Identifiers

| Field             | Description                                            |
| ----------------- | ------------------------------------------------------ |
| `isbn`            | ISBN                                                   |
| `issn`            | ISSN                                                   |
| `ismn`            | ISMN                                                   |
| `standard_number` | Any other standard number (overrides isbn/issn if set) |

### Thesis-specific

| Field         | Description                          |
| ------------- | ------------------------------------ |
| `thesis_type` | e.g. `PhD thesis`, `Master's thesis` |

### Supported reference types

`JournalArticle`, `ArticleInAPeriodical`, `Book`, `BookSection`,
`ConferenceProceedings`, `Report`, `Misc`, `Patent`

The `type` field is case-insensitive and accepts common BibTeX/biblatex aliases
such as `article`, `inbook`, `inproceedings`, `phdthesis`, `techreport`,
`online`, etc.  See `word_xml.py` for the full mapping.

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
- tag: Vaswani2017
  doi: 10.48550/arXiv.1706.03762

- tag: OpenAI2023
  type: online
  title: "ChatGPT: Optimizing Language Models for Dialogue"
  year: 2023
  month: "3"
  day: "14"
  authors:
    - last: OpenAI
  url: https://openai.com/blog/chatgpt
  language: english

- tag: NIST2023
  type: techreport
  title: "Artificial Intelligence Risk Management Framework (AI RMF 1.0)"
  year: 2023
  authors:
    - last: "National Institute of Standards and Technology"
  publisher: "National Institute of Standards and Technology"
  url: https://doi.org/10.6028/NIST.AI.100-1
  standard_number: "NIST AI 100-1"
  language: english
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
| `bib2word/languages.py`    | Mapping language names/codes to Word LCIDs         |
| `bib2word/word_xml.py`     | Building and serializing the Word XML              |

## License

MIT
