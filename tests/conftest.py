from pathlib import Path

import pytest
import requests

DATA_DIR = Path(__file__).parent / "data"


class FakeResponse:
    def __init__(self, payload=None, status_code=200, json_error=False):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error")

    def json(self):
        if self.json_error:
            raise ValueError("Expecting value")
        return self.payload


@pytest.fixture
def data_dir() -> Path:
    return DATA_DIR


@pytest.fixture
def fake_get(monkeypatch):
    """Replace ``requests.get`` in bib2word.doi; returns a dict of DOI -> response.

    Requests are recorded in ``responses.calls``. Unknown DOIs return a 404.
    """

    class Responses(dict):
        calls: list[str]

    responses = Responses()
    responses.calls = []

    def get(url, headers=None, timeout=None):
        doi = url.removeprefix("https://dx.doi.org/")
        responses.calls.append(doi)
        response = responses.get(doi)
        if isinstance(response, Exception):
            raise response
        return response or FakeResponse(status_code=404)

    monkeypatch.setattr("bib2word.doi.requests.get", get)
    return responses


@pytest.fixture(autouse=True)
def no_network(monkeypatch, request):
    """Fail loudly if a test tries to hit the network without ``fake_get``."""
    if "fake_get" in request.fixturenames:
        return

    def get(*args, **kwargs):
        raise AssertionError("unexpected network access")

    monkeypatch.setattr("bib2word.doi.requests.get", get)
