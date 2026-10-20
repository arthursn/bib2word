import pytest

from bib2word.languages import lang_to_lcid


@pytest.mark.parametrize(
    "lang, expected",
    [
        ("english", "1033"),
        ("en-GB", "1033"),
        (" French ", "1036"),
        ("pt-br", "1046"),
        ("ngerman", "1031"),
        ("ja", "1041"),
        ("", "1033"),
        ("klingon", "1033"),
    ],
)
def test_lang_to_lcid(lang, expected):
    assert lang_to_lcid(lang) == expected
