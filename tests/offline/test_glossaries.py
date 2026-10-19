# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import datetime
import io

import deepl
import pytest

from .client import make_translator, url
from .matchers import bodyless_request, json_request

GLOSSARY_JSON = {
    "glossary_id": "g-1",
    "name": "glossary",
    "ready": True,
    "source_lang": "en",
    "target_lang": "de",
    "creation_time": "2021-08-03T14:16:18.329Z",
    "entry_count": 2,
}


def create_body(entries_format, entries, source_lang="EN", target_lang="DE"):
    return {
        "name": "glossary",
        "source_lang": source_lang,
        "target_lang": target_lang,
        "entries_format": entries_format,
        "entries": entries,
    }


def test_sends_tsv_entries_when_creating_glossary(mocked):
    mocked.post(
        url("v2/glossaries"),
        json=GLOSSARY_JSON,
        match=json_request(create_body("tsv", "Hello\tHallo\nA\tB")),
    )

    make_translator().create_glossary(
        "glossary", "EN", "DE", {"Hello": "Hallo", " A ": "B "}
    )


def test_sends_base_languages_when_creating_glossary(mocked):
    mocked.post(
        url("v2/glossaries"),
        json=GLOSSARY_JSON,
        match=json_request(create_body("tsv", "a\tb", "EN", "PT")),
    )

    make_translator().create_glossary(
        "glossary",
        deepl.Language.ENGLISH_AMERICAN,
        "pt-br",
        {"a": "b"},
    )


@pytest.mark.parametrize(
    "csv_data",
    [
        "a,b\n",
        io.StringIO("a,b\n"),
    ],
)
def test_sends_csv_data_when_creating_glossary_from_csv(mocked, csv_data):
    mocked.post(
        url("v2/glossaries"),
        json=GLOSSARY_JSON,
        match=json_request(create_body("csv", "a,b\n")),
    )

    make_translator().create_glossary_from_csv(
        "glossary", "EN", "DE", csv_data
    )


@pytest.mark.parametrize("csv_data", [b"a,b\n", io.BytesIO(b"a,b\n")])
def test_sends_csv_bytes_when_creating_glossary_from_csv(mocked, csv_data):
    mocked.post(
        url("v2/glossaries"),
        json=GLOSSARY_JSON,
        match=json_request(create_body("csv", "a,b\n")),
    )

    make_translator().create_glossary_from_csv(
        "glossary", "EN", "DE", csv_data
    )


def test_raises_when_glossary_csv_is_not_text():
    reader = io.StringIO()
    reader.read = lambda: 5  # type: ignore[assignment,method-assign]

    with pytest.raises(ValueError, match="Entries of the glossary"):
        make_translator().create_glossary_from_csv(
            "glossary", "EN", "DE", reader
        )


def test_raises_when_creating_glossary_with_invalid_input():
    translator = make_translator()

    with pytest.raises(ValueError, match="name must not be empty"):
        translator.create_glossary("", "EN", "DE", {"a": "b"})
    with pytest.raises(ValueError, match="entries must not be empty"):
        translator.create_glossary("glossary", "EN", "DE", {})
    with pytest.raises(ValueError, match="invalid character"):
        translator.create_glossary("glossary", "EN", "DE", {"a\tb": "c"})
    with pytest.raises(ValueError, match="not a valid string"):
        translator.create_glossary("glossary", "EN", "DE", {"": "c"})


def test_parses_glossary_info(mocked):
    mocked.post(url("v2/glossaries"), json=GLOSSARY_JSON)

    glossary = make_translator().create_glossary(
        "glossary", "EN", "DE", {"a": "b"}
    )

    assert glossary.glossary_id == "g-1"
    assert glossary.ready is True
    assert glossary.source_lang == "EN"
    assert glossary.target_lang == "DE"
    assert glossary.entry_count == 2
    assert glossary.creation_time == datetime.datetime(
        2021, 8, 3, 14, 16, 18, 329000, tzinfo=datetime.timezone.utc
    )
    assert str(glossary) == 'Glossary "glossary" (g-1)'


def test_parses_glossary_creation_time_with_nanoseconds(mocked):
    mocked.get(
        url("v2/glossaries/g-1"),
        json={
            **GLOSSARY_JSON,
            "creation_time": "2021-08-03T14:16:18.1234567Z",
        },
        match=bodyless_request(),
    )

    glossary = make_translator().get_glossary("g-1")

    assert glossary.creation_time.microsecond == 123456


def test_sends_get_when_getting_glossary(mocked):
    mocked.get(
        url("v2/glossaries/g-1"),
        json=GLOSSARY_JSON,
        match=bodyless_request(),
    )

    make_translator().get_glossary("g-1")


def test_parses_glossary_list(mocked):
    mocked.get(
        url("v2/glossaries"),
        json={"glossaries": [GLOSSARY_JSON, {**GLOSSARY_JSON, "name": "b"}]},
        match=bodyless_request(),
    )

    glossaries = make_translator().list_glossaries()

    assert [glossary.name for glossary in glossaries] == ["glossary", "b"]


def test_returns_empty_list_when_no_glossaries(mocked):
    mocked.get(url("v2/glossaries"), json={})

    assert make_translator().list_glossaries() == []


@pytest.mark.parametrize(
    "glossary",
    ["g-1", deepl.GlossaryInfo.from_json(GLOSSARY_JSON)],
)
def test_sends_tsv_accept_header_when_getting_entries(mocked, glossary):
    mocked.get(
        url("v2/glossaries/g-1/entries"),
        body="Hello\tHallo\n\nA%=&\tB&=%\n",
        match=[
            *bodyless_request(),
            deepl_accept_tsv,
        ],
    )

    entries = make_translator().get_glossary_entries(glossary)

    assert entries == {"Hello": "Hallo", "A%=&": "B&=%"}


def deepl_accept_tsv(request):
    accept = request.headers.get("Accept")
    return accept == "text/tab-separated-values", f"Accept: {accept}"


def test_raises_when_glossary_entries_have_no_separator(mocked):
    mocked.get(url("v2/glossaries/g-1/entries"), body="no separator")

    with pytest.raises(ValueError, match="does not contain separator"):
        make_translator().get_glossary_entries("g-1")


@pytest.mark.parametrize(
    "glossary",
    ["g-1", deepl.GlossaryInfo.from_json(GLOSSARY_JSON)],
)
def test_sends_delete_when_deleting_glossary(mocked, glossary):
    mocked.delete(
        url("v2/glossaries/g-1"), status=204, match=bodyless_request()
    )

    assert make_translator().delete_glossary(glossary) is None


@pytest.mark.parametrize(
    "method, path, call",
    [
        ("GET", "v2/glossaries/g-1", lambda t: t.get_glossary("g-1")),
        (
            "GET",
            "v2/glossaries/g-1/entries",
            lambda t: t.get_glossary_entries("g-1"),
        ),
        ("DELETE", "v2/glossaries/g-1", lambda t: t.delete_glossary("g-1")),
        ("GET", "v2/glossaries", lambda t: t.list_glossaries()),
        (
            "POST",
            "v2/glossaries",
            lambda t: t.create_glossary("glossary", "EN", "DE", {"a": "b"}),
        ),
    ],
)
def test_raises_glossary_not_found_when_server_returns_404(
    mocked, method, path, call
):
    mocked.add(method, url(path), status=404, json={"message": "gone"})

    with pytest.raises(
        deepl.GlossaryNotFoundException, match="Glossary not found.*gone"
    ) as exc_info:
        call(make_translator())

    assert exc_info.value.http_status_code == 404
