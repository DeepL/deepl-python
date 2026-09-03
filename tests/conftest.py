# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import deepl
import os
import pathlib
from deepl.api_data import (
    MultilingualGlossaryDictionaryEntries,
    MultilingualGlossaryInfo,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
import pytest
from typing import Callable, List, Optional
from typing_extensions import Protocol
import uuid


# Set environment variables to change this configuration.
# Example: export DEEPL_SERVER_URL=http://localhost:3000/
#          export DEEPL_MOCK_SERVER_PORT=3000
#          export DEEPL_PROXY_URL=http://localhost:3001/
#          export DEEPL_MOCK_PROXY_SERVER_PORT=3001
#
# supported use cases:
#  - using real API
#      - user needs to configure their auth_key
#  - using a local mock server
#      - user needs to configure: server_url and set mock_server_port
#      - auth_key can be set empty
#  - using a real server with different IP (e.g. for testing)
#      - user needs to configure their auth_key and server_url
class Config(BaseSettings):
    auth_key: Optional[str] = None
    server_url: Optional[str] = None
    mock_server_port: Optional[int] = None
    proxy_url: Optional[str] = None
    mock_proxy_server_port: Optional[int] = None

    model_config = SettingsConfigDict(env_prefix="DEEPL_")


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def server(config):
    class Server:
        def __init__(self):
            self.headers = {}
            self.is_mock_server = config.mock_server_port is not None
            if self.is_mock_server:
                self.server_url = config.server_url
                self.auth_key = "mock_server"
                uu = str(uuid.uuid1())
                session_uuid = f"{os.getenv('PYTEST_CURRENT_TEST')}/{uu}"
                self.headers["mock-server-session"] = session_uuid
                self.proxy = config.proxy_url
            else:
                self.auth_key = config.auth_key
                self.server_url = config.server_url
                self.proxy = config.proxy_url

        def no_response(self, count):
            """Instructs the mock server to ignore N requests from this
            session, giving no response."""
            if self.is_mock_server:
                self.headers["mock-server-session-no-response-count"] = str(
                    count
                )

        def respond_with_429(self, count):
            """Instructs the mock server to reject N /translate requests from
            this session with 429 status codes."""
            if self.is_mock_server:
                self.headers["mock-server-session-429-count"] = str(count)

        def init_character_limit(self, count):
            """Instructs the mock server to initialize user accounts created by
            this session with given character limit."""
            if self.is_mock_server:
                self.headers["mock-server-session-init-character-limit"] = str(
                    count
                )

        def init_document_limit(self, count):
            """Instructs the mock server to initialize user accounts created by
            this session with given document limit."""
            if self.is_mock_server:
                self.headers["mock-server-session-init-document-limit"] = str(
                    count
                )

        def init_team_document_limit(self, count):
            """Instructs the mock server to initialize user accounts created by
            this session with given team document limit."""
            if self.is_mock_server:
                self.headers[
                    "mock-server-session-init-team-document-limit"
                ] = str(count)

        def set_doc_failure(self, count):
            """Instructs the mock server to fail during translation of N
            documents during this session."""
            if self.is_mock_server:
                self.headers["mock-server-session-doc-failure"] = str(count)

        def set_doc_queue_time(self, milliseconds):
            """Instructs the mock server to queue documents for specified time
            before translation."""
            if self.is_mock_server:
                self.headers["mock-server-session-doc-queue-time"] = str(
                    milliseconds
                )

        def set_doc_translate_time(self, milliseconds):
            """Instructs the mock server to translate documents within
            specified time."""
            if self.is_mock_server:
                self.headers["mock-server-session-doc-translate-time"] = str(
                    milliseconds
                )

        def set_tm_job_processing_polls(self, count):
            """Instructs the mock server to report a non-terminal status for
            translation memory jobs for the given number of polls before
            completing them."""
            if self.is_mock_server:
                self.headers["mock-server-session-tm-job-processing-polls"] = (
                    str(count)
                )

        def expect_proxy(self, value: bool = True):
            """Instructs the mock server to only accept requests via the
            proxy."""
            if self.is_mock_server:
                self.headers["mock-server-session-expect-proxy"] = (
                    "1" if value else "0"
                )

    return Server()


def _make_translator(server, auth_key=None, proxy=None):
    """Returns a deepl.Translator for the specified server test fixture.
    The server auth_key is used unless specifically overridden."""
    if auth_key is None:
        auth_key = server.auth_key
    translator = deepl.Translator(
        auth_key, server_url=server.server_url, proxy=proxy
    )

    # If the server test fixture has custom headers defined, update the
    # translator headers and replace with the server headers dictionary.
    # Note: changing the underlying object is necessary because some tests
    # make changes to the headers during tests.
    if server.headers:
        server.headers.update(translator.headers)
        translator.headers = server.headers
    return translator


def _make_deepl_client(server, auth_key=None, proxy=None):
    """Returns a deepl.DeepLClient for the specified server test fixture.
    The server auth_key is used unless specifically overridden."""
    if auth_key is None:
        auth_key = server.auth_key
    deepl_client = deepl.DeepLClient(
        auth_key, server_url=server.server_url, proxy=proxy
    )

    # If the server test fixture has custom headers defined, update the
    # translator headers and replace with the server headers dictionary.
    # Note: changing the underlying object is necessary because some tests
    # make changes to the headers during tests.
    if server.headers:
        server.headers.update(deepl_client.headers)
        deepl_client.headers = server.headers
    return deepl_client


@pytest.fixture
def translator(server):
    """Returns a deepl.Translator to use in all tests taking a parameter
    'translator'."""
    return _make_translator(server)


# TODO Replace all uses of `translator` above with this and delete the
# duplicated code.
@pytest.fixture
def deepl_client(server):
    """Returns a deepl.DeepLClient to use in all tests taking a parameter
    'deepl_client'."""
    return _make_deepl_client(server)


@pytest.fixture
def translator_with_random_auth_key(server):
    """Returns a deepl.Translator with randomized authentication key,
    for use in mock-server tests."""
    return _make_translator(server, auth_key=str(uuid.uuid1()))


@pytest.fixture
def translator_with_random_auth_key_and_proxy(server):
    """Returns a deepl.Translator with randomized authentication key,
    for use in mock-server tests."""
    return _make_translator(
        server, auth_key=str(uuid.uuid1()), proxy=server.proxy
    )


@pytest.fixture
def cleanup_matching_glossaries(deepl_client):
    """
    Fixture function to remove all glossaries from the server matching the
    given predicate. Can be used, for example, to remove all glossaries with a
    matching name.

    Usage example:
        def test_example(cleanup_matching_glossaries):
            ...
            cleanup_matching_glossaries(
                lambda glossary: glossary.name.startswith("test ")
            )
    """

    def do_cleanup(predicate: Callable[[deepl.GlossaryInfo], bool]):
        glossaries = deepl_client.list_multilingual_glossaries()
        for glossary in glossaries:
            if predicate(glossary):
                try:
                    deepl_client.delete_multilingual_glossary(glossary)
                except deepl.DeepLException:
                    pass

    return do_cleanup


class ManagedGlossary:
    """
    Utility content-manager class to create a test glossary and ensure its
    deletion at the end of a test.
    """

    def __init__(
        self,
        translator: deepl.Translator,
        glossary_name: str,
        source_lang,
        target_lang,
        entries: dict,
    ):
        self._translator = translator
        self._created_glossary = translator.create_glossary(
            glossary_name, source_lang, target_lang, entries
        )

    def __enter__(self) -> deepl.GlossaryInfo:
        return self._created_glossary

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._translator.delete_glossary(
                self._created_glossary.glossary_id
            )
        except deepl.DeepLException:
            pass


class ManagedMultilingualGlossary:
    """
    Utility content-manager class to create a test glossary and ensure its
    deletion at the end of a test.
    """

    def __init__(
        self,
        deepl_client,
        glossary_name: str,
        dictionaries: List[MultilingualGlossaryDictionaryEntries],
    ):
        self.deepl_client = deepl_client
        self._created_glossary = deepl_client.create_multilingual_glossary(
            glossary_name, dictionaries
        )

    def __enter__(self) -> MultilingualGlossaryInfo:
        return self._created_glossary

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.deepl_client.delete_multilingual_glossary(
                self._created_glossary.glossary_id
            )
        except deepl.DeepLException:
            pass


class CreateManagedGlossaryFunc(Protocol):
    """Helper class for type hints."""

    def __call__(
        self,
        source_lang: str = "EN",
        target_lang: str = "DE",
        entries: Optional[dict] = None,
        glossary_name_suffix: str = "",
    ) -> ManagedGlossary:
        pass


class CreateManagedMultilingualGlossaryFunc(Protocol):
    """Helper class for type hints."""

    def __call__(
        self,
        dictionaries: List[MultilingualGlossaryDictionaryEntries],
        glossary_name_suffix: str = "",
    ) -> ManagedMultilingualGlossary:
        pass


@pytest.fixture
def glossary_manager(translator, glossary_name) -> CreateManagedGlossaryFunc:
    """
    Fixture function that may be used to create context-managed test v2
    glossaries, named using the current test. May be called multiple times in
    a test to create multiple glossaries, ideally with a different suffix for
    each glossary.

    Usage example:
        def test_example(glossary_manager):
            with glossary_manager(
                entries={"a": "b"}, glossary_name_suffix="1"
            ) as glossary1:
                ...
    """

    def create_managed_glossary(
        source_lang: str = "EN",
        target_lang: str = "DE",
        entries: Optional[dict] = None,
        glossary_name_suffix: str = "",
    ):
        if not entries:
            entries = {"Hello": "Hallo"}
        return ManagedGlossary(
            translator,
            f"{glossary_name}{glossary_name_suffix}",
            source_lang,
            target_lang,
            entries,
        )

    return create_managed_glossary


@pytest.fixture
def multilingual_glossary_manager(
    deepl_client, glossary_name
) -> CreateManagedMultilingualGlossaryFunc:
    """
    Fixture function that may be used to create context-managed test
    glossaries, named using the current test. May be called multiple times in
    a test to create multiple glossaries, ideally with a different suffix for
    each glossary.

    Usage example:
        def test_example(glossary_manager):
            with glossary_manager(
                entries={"a": "b"}, glossary_name_suffix="1"
            ) as glossary1:
                ...
    """

    def create_managed_glossary(
        dictionaries: List[MultilingualGlossaryDictionaryEntries],
        glossary_name_suffix: str = "",
    ):
        return ManagedMultilingualGlossary(
            deepl_client,
            f"{glossary_name}{glossary_name_suffix}",
            dictionaries,
        )

    return create_managed_glossary


@pytest.fixture
def glossary_name(request) -> str:
    """Returns a suitable glossary name to be used in the test"""
    test_name = request.node.name
    new_uuid = str(uuid.uuid1())
    return f"deepl-python-test-glossary: {test_name} {new_uuid}"


@pytest.fixture
def example_document_path(tmpdir):
    tmpdir = pathlib.Path(tmpdir)
    path = tmpdir / "input" / "example_document.txt"
    path.parent.mkdir()
    path.write_text(example_text["EN"])
    return path


@pytest.fixture
def example_glossary_csv(tmpdir):
    tmpdir = pathlib.Path(tmpdir)
    content = (
        "sourceEntry1,targetEntry1,en,de\n"
        '"source""Entry","target,Entry",en,de'
    )
    path = tmpdir / "glossary" / "example_glossary.csv"
    path.parent.mkdir()
    path.write_text(content)
    return path


@pytest.fixture
def example_glossary_csv_entries():
    return {
        "sourceEntry1": "targetEntry1",
        'source"Entry': "target,Entry",
    }


@pytest.fixture
def example_document_translation():
    return example_text["DE"]


@pytest.fixture
def example_large_document_translation():
    return (example_text["DE"] + "\n") * 1000


@pytest.fixture
def input_dir_path(tmpdir):
    tmpdir = pathlib.Path(tmpdir)
    path = tmpdir / "input"
    path.mkdir(exist_ok=True)
    return path


@pytest.fixture
def output_dir_path(tmpdir):
    tmpdir = pathlib.Path(tmpdir)
    path = tmpdir / "output"
    path.mkdir(exist_ok=True)
    return path


@pytest.fixture
def example_large_document_path(input_dir_path):
    path = input_dir_path / "example_document.txt"
    path.write_text((example_text["EN"] + "\n") * 1000)
    return path


@pytest.fixture
def output_document_path(output_dir_path):
    return output_dir_path / "example_document.txt"


# Decorate test functions with "@needs_mock_server" to skip them if a real
#  server is used
needs_mock_server = pytest.mark.skipif(
    Config().mock_server_port is None,
    reason="this test requires a mock server",
)
# Decorate test functions with "@needs_mock_proxy_server" to skip them if a
#  real server is used or mock proxy server is not configured
needs_mock_proxy_server = pytest.mark.skipif(
    Config().mock_proxy_server_port is None
    or Config().mock_server_port is None,
    reason="this test requires a mock proxy server",
)
# Decorate test functions with "@needs_real_server" to skip them if a mock
#  server is used
needs_real_server = pytest.mark.skipif(
    not (Config().mock_server_port is None),
    reason="this test requires a real server",
)


example_text = {
    "AR": "شعاع البروتون",
    "BG": "протонен лъч",
    "CS": "protonový paprsek",
    "DA": "protonstråle",
    "DE": "Protonenstrahl",
    "EL": "δέσμη πρωτονίων",
    "EN": "proton beam",
    "EN-US": "proton beam",
    "EN-GB": "proton beam",
    "ES": "haz de protones",
    "ET": "prootonikiirgus",
    "FI": "protonisäde",
    "FR": "faisceau de protons",
    "HU": "protonnyaláb",
    "ID": "berkas proton",
    "IT": "fascio di protoni",
    "JA": "陽子ビーム",
    "KO": "양성자 빔",
    "LT": "protonų spindulys",
    "LV": "protonu staru kūlis",
    "NB": "protonstråle",
    "NL": "protonenbundel",
    "PL": "wiązka protonów",
    "PT": "feixe de prótons",
    "PT-BR": "feixe de prótons",
    "PT-PT": "feixe de prótons",
    "RO": "fascicul de protoni",
    "RU": "протонный луч",
    "SK": "protónový lúč",
    "SL": "protonski žarek",
    "SV": "protonstråle",
    "TR": "proton ışını",
    "UK": "протонний пучок",
    "ZH": "质子束",
}
