# Copyright 2022 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import datetime
import io

import deepl
import pytest
from deepl.api_data import (
    TranslationMemoryExport,
    TranslationMemoryImport,
    TranslationMemoryInfo,
    TranslationMemoryJob,
    TranslationMemorySegments,
)

from ..fixtures import example_tmx
from .client import make_deepl_client, url
from .matchers import bodyless_request, json_request, storage_request

UPLOAD_URL = "https://storage.example.com/tm/upload?signature=abc"
DOWNLOAD_URL = "https://storage.example.com/tm/download?signature=def"
TM_JSON = {
    "translation_memory_id": "tm-1",
    "name": "memory",
    "source_language": "en",
    "target_languages": ["de", "fr"],
    "segment_count": 7,
    "creation_time": "2021-08-03T14:16:18.329Z",
    "updated_time": "2021-08-03T14:16:18Z",
}
IMPORT_JSON = {
    "job_id": "job-1",
    "upload_url": UPLOAD_URL,
    "expires_at": "2021-08-03T15:16:18.329Z",
}


def job_json(status, operation="import", **result):
    return {
        "job_id": "job-1",
        "operation": operation,
        "product": "translation_memory",
        "parameters": {"translation_memory_id": "tm-1"},
        "source_file": {"content_type": "application/xml"},
        "results": [{"status": status, **result}],
    }


def reply_with_job(mocked, status, operation="import", **result):
    mocked.get(
        url("v3/translation_memories/jobs/job-1"),
        json=job_json(status, operation, **result),
        match=bodyless_request(),
    )


def test_sends_query_when_listing_translation_memories(mocked):
    mocked.get(
        url("v3/translation_memories"),
        json={"translation_memories": [TM_JSON]},
        match=bodyless_request({"page": "2", "page_size": "25"}),
    )

    make_deepl_client().list_translation_memories(page=2, page_size=25)


def test_parses_translation_memory_list(mocked):
    mocked.get(
        url("v3/translation_memories"),
        json={
            "translation_memories": [
                TM_JSON,
                {
                    "translation_memory_id": "tm-2",
                    "name": "other",
                    "source_language": "de",
                },
            ]
        },
        match=bodyless_request(),
    )

    memories = make_deepl_client().list_translation_memories()

    first, second = memories
    assert isinstance(first, TranslationMemoryInfo)
    assert first.creation_time == datetime.datetime(
        2021, 8, 3, 14, 16, 18, 329000, tzinfo=datetime.timezone.utc
    )
    assert first.updated_time == datetime.datetime(
        2021, 8, 3, 14, 16, 18, tzinfo=datetime.timezone.utc
    )
    assert second.target_languages == []
    assert second.segment_count == 0
    assert second.creation_time is None
    assert str(first) == 'TranslationMemory "memory" (tm-1)'


@pytest.mark.parametrize(
    "memory", ["tm-1", TranslationMemoryInfo.from_json(TM_JSON)]
)
def test_sends_get_when_getting_translation_memory(mocked, memory):
    mocked.get(
        url("v3/translation_memories/tm-1"),
        json=TM_JSON,
        match=bodyless_request(),
    )

    make_deepl_client().get_translation_memory(memory)


@pytest.mark.parametrize(
    "memory", ["tm-1", TranslationMemoryInfo.from_json(TM_JSON)]
)
def test_sends_delete_when_deleting_translation_memory(mocked, memory):
    mocked.delete(
        url("v3/translation_memories/tm-1"),
        status=204,
        match=bodyless_request(),
    )

    assert make_deepl_client().delete_translation_memory(memory) is None


def test_escapes_translation_memory_id_in_path(mocked):
    mocked.get(
        url("v3/translation_memories/a%2Fb%3Fc%20d/segments"),
        json={"segments": [], "segment_count": 0},
        match=bodyless_request(),
    )

    make_deepl_client().list_translation_memory_segments("a/b?c d")


def test_escapes_job_id_in_path_once_when_waiting(mocked):
    mocked.get(
        url("v3/translation_memories/jobs/a%2Fb%3Fc%20d"),
        json=job_json("completed"),
        match=bodyless_request(),
    )

    make_deepl_client().wait_until_translation_memory_job_done("a/b?c d")


def test_raises_for_empty_translation_memory_and_job_ids():
    client = make_deepl_client()

    with pytest.raises(ValueError, match="translation_memory must not"):
        client.get_translation_memory("")
    with pytest.raises(ValueError, match="translation_memory must not"):
        client.delete_translation_memory("")
    with pytest.raises(ValueError, match="translation_memory must not"):
        client.list_translation_memory_segments("")
    with pytest.raises(ValueError, match="translation_memory must not"):
        client.create_translation_memory_export("")
    with pytest.raises(ValueError, match="job must not be empty"):
        client.get_translation_memory_job("")


def test_sends_segment_query_options(mocked):
    mocked.get(
        url("v3/translation_memories/tm-1/segments"),
        json={"segments": []},
        match=bodyless_request(
            {
                "page_size": "5",
                "page_cursor": "cursor-1",
                "filter_text": "hello world",
                "filter_case_sensitive": "false",
            }
        ),
    )

    make_deepl_client().list_translation_memory_segments(
        "tm-1",
        page_size=5,
        page_cursor="cursor-1",
        filter_text="hello world",
        filter_case_sensitive=False,
    )

    assert "filter_text=hello%20world" in mocked.calls[0].request.url


def test_sends_segment_request_without_query_by_default(mocked):
    mocked.get(
        url("v3/translation_memories/tm-1/segments"),
        json={"segments": []},
        match=bodyless_request(),
    )

    make_deepl_client().list_translation_memory_segments(
        TranslationMemoryInfo.from_json(TM_JSON)
    )


def test_parses_translation_memory_segments(mocked):
    mocked.get(
        url("v3/translation_memories/tm-1/segments"),
        json={
            "segment_count": 12,
            "next_page_cursor": "next",
            "segments": [
                {
                    "source_segment_id": "s-1",
                    "source_text": "Hello",
                    "targets": [
                        {
                            "target_segment_id": "t-1",
                            "target_language": "de",
                            "target_text": "Hallo",
                            "last_used_time": "2021-08-03T14:16:18.329Z",
                        }
                    ],
                },
                {"source_segment_id": "s-2", "source_text": "Bye"},
            ],
        },
    )

    page = make_deepl_client().list_translation_memory_segments("tm-1")

    assert isinstance(page, TranslationMemorySegments)
    assert len(page) == 2
    first, second = list(page)
    assert str(first.targets[0]) == "de: Hallo"
    assert first.targets[0].last_used_time == datetime.datetime(
        2021, 8, 3, 14, 16, 18, 329000, tzinfo=datetime.timezone.utc
    )
    assert second.targets == []


@pytest.mark.parametrize(
    "kwargs, body",
    [
        (
            {},
            {"source_file": {"file_name": "a.tmx", "content_length": 10}},
        ),
        (
            {"content_type": "text/xml", "display_name": "Name"},
            {
                "source_file": {
                    "file_name": "a.tmx",
                    "content_length": 10,
                    "content_type": "text/xml",
                },
                "parameters": {"display_name": "Name"},
            },
        ),
    ],
)
def test_sends_file_description_when_creating_import(mocked, kwargs, body):
    mocked.post(
        url("v3/translation_memories/import"),
        json=IMPORT_JSON,
        match=json_request(body),
    )

    created = make_deepl_client().create_translation_memory_import(
        "a.tmx", 10, **kwargs
    )

    assert isinstance(created, TranslationMemoryImport)
    assert created.expires_at == datetime.datetime(
        2021, 8, 3, 15, 16, 18, 329000, tzinfo=datetime.timezone.utc
    )
    assert str(created) == "TranslationMemoryImport (job-1)"


def test_sends_extra_body_parameters_last_when_creating_import(mocked):
    mocked.post(
        url("v3/translation_memories/import"),
        json=IMPORT_JSON,
        match=json_request(
            {
                "source_file": {"file_name": "a.tmx", "content_length": 10},
                "parameters": {"display_name": "Extra"},
                "custom": [1, True],
            }
        ),
    )

    make_deepl_client().create_translation_memory_import(
        "a.tmx",
        10,
        display_name="Name",
        extra_body_parameters={
            "parameters": {"display_name": "Extra"},
            "custom": [1, True],
        },
    )


def test_raises_when_creating_import_with_invalid_file():
    client = make_deepl_client()

    with pytest.raises(ValueError, match="file_name must not be empty"):
        client.create_translation_memory_import("", 10)
    with pytest.raises(ValueError, match="greater than 0"):
        client.create_translation_memory_import("a.tmx", 0)


@pytest.mark.parametrize(
    "upload, content",
    [
        (UPLOAD_URL, io.BytesIO(b"<tmx/>")),
        (TranslationMemoryImport("job-1", UPLOAD_URL), b"<tmx/>"),
    ],
)
def test_uploads_file_content_to_storage_without_authorization(
    mocked, upload, content
):
    mocked.put(
        UPLOAD_URL,
        status=200,
        match=storage_request("application/xml", "<tmx/>"),
    )

    make_deepl_client().upload_translation_memory_file(upload, content)


def test_sends_given_content_type_when_uploading_file(mocked):
    mocked.put(
        UPLOAD_URL,
        match=storage_request("text/xml", "<tmx/>"),
    )

    make_deepl_client().upload_translation_memory_file(
        UPLOAD_URL, b"<tmx/>", content_type="text/xml"
    )


def test_raises_when_uploading_file_without_url():
    with pytest.raises(ValueError, match="upload_url must not be empty"):
        make_deepl_client().upload_translation_memory_file("", b"x")


def test_raises_with_status_and_detail_when_storage_rejects_upload(mocked):
    mocked.put(UPLOAD_URL, status=403, body="expired")

    with pytest.raises(
        deepl.DeepLException,
        match="uploading translation memory file, HTTP status: 403, "
        "detail: expired",
    ) as exc_info:
        make_deepl_client().upload_translation_memory_file(UPLOAD_URL, b"x")

    assert exc_info.value.http_status_code == 403


@pytest.mark.parametrize("status, reused", [(200, True), (202, False)])
def test_marks_export_as_reused_when_server_returns_200(
    mocked, status, reused
):
    mocked.post(
        url("v3/translation_memories/tm-1/export"),
        status=status,
        json={
            "job_id": "job-1",
            "parameters": {"translation_memory_id": "tm-1"},
        },
        match=bodyless_request(),
    )

    export = make_deepl_client().create_translation_memory_export(
        TranslationMemoryInfo.from_json(TM_JSON)
    )

    assert isinstance(export, TranslationMemoryExport)
    assert export.translation_memory_id == "tm-1"
    assert export.reused_existing is reused
    assert str(export) == "TranslationMemoryExport (job-1)"


@pytest.mark.parametrize(
    "job", ["job-1", TranslationMemoryJob("job-1", "", [])]
)
def test_parses_translation_memory_job(mocked, job):
    mocked.get(
        url("v3/translation_memories/jobs/job-1"),
        json={
            **job_json(
                "completed",
                translation_memory_id="tm-1",
                skipped_segment_count=2,
                download_url=DOWNLOAD_URL,
                expires_at="2021-08-03T15:16:18.329Z",
            ),
            "parameters": {
                "translation_memory_id": "tm-1",
                "display_name": "Name",
            },
            "source_file": {"content_type": "text/xml", "content_length": 9},
        },
        match=bodyless_request(),
    )

    result = make_deepl_client().get_translation_memory_job(job)

    assert result.status == "completed"
    assert result.done and result.ok
    assert result.translation_memory_id == "tm-1"
    assert result.display_name == "Name"
    assert result.source_content_type == "text/xml"
    assert result.source_content_length == 9
    assert result.result.skipped_segment_count == 2
    assert result.result.download_url == DOWNLOAD_URL
    assert str(result) == "TranslationMemoryJob import (job-1): completed"


@pytest.mark.parametrize(
    "status, done, ok",
    [
        ("awaiting_input", False, True),
        ("processing", False, True),
        ("completed", True, True),
        ("downloaded", True, True),
        ("failed", True, False),
        ("expired", True, False),
    ],
)
def test_derives_job_progress_from_status(mocked, status, done, ok):
    reply_with_job(mocked, status, error={"message": "bad"})

    job = make_deepl_client().get_translation_memory_job("job-1")

    assert (job.done, job.ok) == (done, ok)
    assert job.result.error_message == "bad"


def test_parses_required_action_of_awaiting_job(mocked):
    reply_with_job(
        mocked, "awaiting_input", status_metadata={"required_action": "upload"}
    )

    job = make_deepl_client().get_translation_memory_job("job-1")

    assert job.result.required_action == "upload"


def test_polls_job_until_it_is_done(mocked):
    reply_with_job(mocked, "awaiting_input")
    reply_with_job(mocked, "completed", translation_memory_id="tm-1")

    job = make_deepl_client().wait_until_translation_memory_job_done("job-1")

    assert job.translation_memory_id == "tm-1"


def test_raises_when_waiting_for_job_exceeds_timeout(mocked):
    reply_with_job(mocked, "processing")

    # A negative timeout is exceeded on the first check without any sleep.
    with pytest.raises(
        deepl.DeepLException, match="Manual timeout of -1s.*memory job"
    ):
        make_deepl_client().wait_until_translation_memory_job_done(
            "job-1", timeout_s=-1
        )


def test_imports_file_by_creating_job_uploading_and_waiting(mocked, tmp_path):
    path = tmp_path / "example.tmx"
    path.write_text(example_tmx)
    size = path.stat().st_size
    mocked.post(
        url("v3/translation_memories/import"),
        json=IMPORT_JSON,
        match=json_request(
            {
                "source_file": {
                    "file_name": "example.tmx",
                    "content_length": size,
                },
                "parameters": {"display_name": "Name"},
            }
        ),
    )
    mocked.put(
        UPLOAD_URL,
        match=storage_request("application/xml", example_tmx),
    )
    reply_with_job(mocked, "completed", translation_memory_id="tm-1")

    job = make_deepl_client().import_translation_memory_from_filepath(
        path, display_name="Name"
    )

    assert job.result.translation_memory_id == "tm-1"


def test_imports_file_with_content_type_and_extra_body_parameters(
    mocked, tmp_path
):
    path = tmp_path / "example.tmx"
    path.write_text(example_tmx)
    mocked.post(
        url("v3/translation_memories/import"),
        json=IMPORT_JSON,
        match=json_request(
            {
                "source_file": {
                    "file_name": "example.tmx",
                    "content_length": path.stat().st_size,
                    "content_type": "text/xml",
                },
                "custom": "value",
            }
        ),
    )
    mocked.put(UPLOAD_URL, match=storage_request("text/xml", example_tmx))
    reply_with_job(mocked, "completed", translation_memory_id="tm-1")

    make_deepl_client().import_translation_memory_from_filepath(
        path,
        content_type="text/xml",
        extra_body_parameters={"custom": "value"},
    )


def test_raises_when_imported_file_does_not_exist(tmp_path):
    with pytest.raises(ValueError, match="file does not exist"):
        make_deepl_client().import_translation_memory_from_filepath(
            tmp_path / "missing.tmx"
        )


def test_raises_with_error_message_when_import_job_fails(mocked, tmp_path):
    path = tmp_path / "example.tmx"
    path.write_text(example_tmx)
    mocked.post(url("v3/translation_memories/import"), json=IMPORT_JSON)
    mocked.put(UPLOAD_URL)
    reply_with_job(mocked, "failed", error={"message": "invalid TMX"})

    with pytest.raises(
        deepl.DeepLException,
        match="Error occurred while importing translation memory: "
        "invalid TMX",
    ):
        make_deepl_client().import_translation_memory_from_filepath(path)


def test_raises_with_unknown_error_when_failed_job_has_no_message(
    mocked, tmp_path
):
    path = tmp_path / "example.tmx"
    path.write_text(example_tmx)
    mocked.post(url("v3/translation_memories/import"), json=IMPORT_JSON)
    mocked.put(UPLOAD_URL)
    reply_with_job(mocked, "expired")

    with pytest.raises(deepl.DeepLException, match="unknown error"):
        make_deepl_client().import_translation_memory_from_filepath(path)


def test_exports_translation_memory_to_file(mocked, tmp_path):
    output_path = tmp_path / "exported.tmx"
    mocked.post(
        url("v3/translation_memories/tm-1/export"),
        status=202,
        json={"job_id": "job-1"},
        match=bodyless_request(),
    )
    reply_with_job(
        mocked, "completed", operation="export", download_url=DOWNLOAD_URL
    )
    mocked.get(DOWNLOAD_URL, body=example_tmx, match=storage_request())

    job = make_deepl_client().export_translation_memory_to_filepath(
        "tm-1", output_path
    )

    assert job.result.download_url == DOWNLOAD_URL
    assert output_path.read_text() == example_tmx


def test_raises_with_error_message_when_export_job_fails(mocked, tmp_path):
    mocked.post(
        url("v3/translation_memories/tm-1/export"),
        status=202,
        json={"job_id": "job-1"},
    )
    reply_with_job(
        mocked, "failed", operation="export", error={"message": "broken"}
    )

    with pytest.raises(
        deepl.DeepLException,
        match="Error occurred while exporting translation memory: broken",
    ):
        make_deepl_client().export_translation_memory_to_filepath(
            "tm-1", tmp_path / "exported.tmx"
        )

    assert not (tmp_path / "exported.tmx").exists()


def test_downloads_export_without_authorization_into_file_object(mocked):
    mocked.get(DOWNLOAD_URL, body=b"<tmx/>", match=storage_request())
    job = TranslationMemoryJob.from_json(
        job_json("completed", "export", download_url=DOWNLOAD_URL)
    )
    output = io.BytesIO()

    result = make_deepl_client().download_translation_memory_export(
        job, output, chunk_size=2
    )

    assert result is None
    assert output.getvalue() == b"<tmx/>"


def test_warns_and_returns_response_when_downloading_export_without_file(
    mocked,
):
    mocked.get(DOWNLOAD_URL, body=b"<tmx/>", match=storage_request())
    job = TranslationMemoryJob.from_json(
        job_json("completed", "export", download_url=DOWNLOAD_URL)
    )

    with pytest.warns(DeprecationWarning, match="pass output_file"):
        response = make_deepl_client().download_translation_memory_export(job)

    assert b"".join(response.iter_content(chunk_size=3)) == b"<tmx/>"


def test_raises_when_downloading_export_without_download_url():
    job = TranslationMemoryJob.from_json(job_json("processing", "export"))

    with pytest.raises(ValueError, match="has no download URL"):
        make_deepl_client().download_translation_memory_export(job)


def test_raises_when_storage_rejects_download(mocked):
    mocked.get(DOWNLOAD_URL, status=404)
    job = TranslationMemoryJob.from_json(
        job_json("completed", "export", download_url=DOWNLOAD_URL)
    )

    with pytest.raises(
        deepl.DeepLException,
        match="downloading translation memory export, HTTP status: 404",
    ):
        make_deepl_client().download_translation_memory_export(
            job, io.BytesIO()
        )


@pytest.mark.parametrize(
    "method, path, call",
    [
        (
            "GET",
            "v3/translation_memories",
            lambda client: client.list_translation_memories(),
        ),
        (
            "GET",
            "v3/translation_memories/tm-1",
            lambda client: client.get_translation_memory("tm-1"),
        ),
        (
            "GET",
            "v3/translation_memories/tm-1/segments",
            lambda client: client.list_translation_memory_segments("tm-1"),
        ),
        (
            "POST",
            "v3/translation_memories/import",
            lambda client: client.create_translation_memory_import(
                "a.tmx", 10
            ),
        ),
        (
            "POST",
            "v3/translation_memories/tm-1/export",
            lambda client: client.create_translation_memory_export("tm-1"),
        ),
        (
            "GET",
            "v3/translation_memories/jobs/job-1",
            lambda client: client.get_translation_memory_job("job-1"),
        ),
    ],
)
@pytest.mark.parametrize(
    "body",
    [
        {"body": "not json"},
        {"json": {"translation_memories": [{}], "segments": [{}]}},
        {
            "json": {
                "translation_memories": [1],
                "segments": [1],
                "results": [1],
            }
        },
    ],
)
def test_raises_deepl_exception_for_malformed_response(
    mocked, method, path, call, body
):
    mocked.add(method, url(path), status=200, **body)

    with pytest.raises(deepl.DeepLException, match="Unexpected response"):
        call(make_deepl_client())
