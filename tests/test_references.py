import pytest

from bib2word.references import load_references, needs_fetch, text


def test_load_references(data_dir):
    refs = load_references(data_dir / "smith2020.yaml")
    assert len(refs) == 1
    assert refs[0]["tag"] == "Smith2020"


@pytest.mark.parametrize(
    "content",
    ["", "tag: Smith2020\n", "just a string\n"],
    ids=["empty", "mapping", "scalar"],
)
def test_load_references_rejects_non_list(tmp_path, content):
    path = tmp_path / "refs.yaml"
    path.write_text(content)
    with pytest.raises(ValueError, match="must contain a list"):
        load_references(path)


def test_load_references_rejects_non_mapping_entry(tmp_path):
    path = tmp_path / "refs.yaml"
    path.write_text("- tag: A\n- 10.1234/abc\n")
    with pytest.raises(ValueError, match="reference #2 is not a mapping"):
        load_references(path)


@pytest.mark.parametrize(
    "mapping, expected",
    [
        ({"k": "  value "}, "value"),
        ({"k": 2020}, "2020"),
        ({"k": None}, ""),
        ({}, ""),
    ],
)
def test_text(mapping, expected):
    assert text(mapping, "k") == expected


@pytest.mark.parametrize(
    "ref, expected",
    [
        ({"doi": "10.1/x"}, True),
        ({"doi": "10.1/x", "tag": "X"}, True),
        ({"doi": "10.1/x", "title": None, "journal": "  "}, True),
        ({}, True),
        ({"doi": "10.1/x", "title": "T"}, False),
        ({"tag": "X", "year": 2020}, False),
    ],
)
def test_needs_fetch(ref, expected):
    assert needs_fetch(ref) is expected
