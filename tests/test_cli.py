import shutil
import xml.etree.ElementTree as ET

import pytest

from bib2word.cli import main
from bib2word.word_xml import WORD_BIB_NS
from tests.conftest import FakeResponse
from tests.test_doi import CSL_PAYLOAD

NS = {"b": WORD_BIB_NS}


def sources_in(path):
    return ET.parse(path).getroot().findall("b:Source", NS)


def test_writes_next_to_input_by_default(tmp_path, data_dir, capsys):
    input_path = tmp_path / "refs.yaml"
    shutil.copy(data_dir / "smith2020.yaml", input_path)

    main([str(input_path)])

    output = tmp_path / "refs.xml"
    assert output.read_text() == (data_dir / "smith2020.xml").read_text()
    assert f"Written to {output}" in capsys.readouterr().err


def test_output_option(tmp_path, data_dir):
    output = tmp_path / "out" / "bib.xml"
    output.parent.mkdir()

    main([str(data_dir / "smith2020.yaml"), "-o", str(output)])

    assert len(sources_in(output)) == 1


def test_doi_only_reference_is_fetched(tmp_path, fake_get, capsys):
    fake_get["10.1/x"] = FakeResponse(CSL_PAYLOAD)
    input_path = tmp_path / "refs.yaml"
    input_path.write_text("- tag: Doe2021\n  doi: 10.1/x\n")

    main([str(input_path)])

    [source] = sources_in(tmp_path / "refs.xml")
    assert source.findtext("b:Tag", namespaces=NS) == "Doe2021"
    assert source.findtext("b:Title", namespaces=NS) == "A Great Paper"
    assert "Fetching metadata for DOI: 10.1/x" in capsys.readouterr().err


def test_reference_with_fields_is_not_fetched(tmp_path, fake_get):
    input_path = tmp_path / "refs.yaml"
    input_path.write_text("- tag: A\n  title: T\n  doi: 10.1/x\n")

    main([str(input_path)])

    assert fake_get.calls == []


def test_failed_fetch_keeps_doi(tmp_path, fake_get, capsys):
    input_path = tmp_path / "refs.yaml"
    input_path.write_text("- tag: Gone\n  doi: 10.1/missing\n")

    main([str(input_path)])

    [source] = sources_in(tmp_path / "refs.xml")
    assert source.findtext("b:Tag", namespaces=NS) == "Gone"
    assert source.findtext("b:DOI", namespaces=NS) == "10.1/missing"
    assert "Warning: could not fetch DOI '10.1/missing'" in capsys.readouterr().err


def test_empty_reference_is_skipped(tmp_path, capsys):
    input_path = tmp_path / "refs.yaml"
    input_path.write_text("- tag: OnlyTag\n- tag: A\n  title: T\n")

    main([str(input_path)])

    [source] = sources_in(tmp_path / "refs.xml")
    assert source.findtext("b:Tag", namespaces=NS) == "A"
    assert "reference #1 has no doi" in capsys.readouterr().err


@pytest.mark.parametrize(
    "content, message",
    [
        ("tag: A\n", "must contain a list"),
        ("- 10.1/x\n", "reference #1 is not a mapping"),
        ("- [unclosed\n", ""),
    ],
    ids=["not-a-list", "not-a-mapping", "invalid-yaml"],
)
def test_bad_input_exits_with_error(tmp_path, capsys, content, message):
    input_path = tmp_path / "refs.yaml"
    input_path.write_text(content)

    with pytest.raises(SystemExit) as exc:
        main([str(input_path)])

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert err.startswith("Error: ")
    assert message in err
    assert not (tmp_path / "refs.xml").exists()


def test_missing_input_file_exits_with_error(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main([str(tmp_path / "nope.yaml")])

    assert exc.value.code == 1
    assert "Error:" in capsys.readouterr().err
