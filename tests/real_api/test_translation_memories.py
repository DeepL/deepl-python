# Copyright 2025 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import io

from ..fixtures import example_tmx
from .client import make_deepl_client
from .helpers import JOB_TIMEOUT_S, get_unique_name


def test_sends_translation_memory_requests_from_import_to_delete():
    client = make_deepl_client()
    name = get_unique_name("translation-memory")
    content = example_tmx.encode("utf-8")
    translation_memory_id = None

    try:
        created = client.create_translation_memory_import(
            "example.tmx", len(content), display_name=name
        )
        assert created.job_id
        assert created.upload_url

        client.upload_translation_memory_file(created, io.BytesIO(content))

        # The translation memory exists only once the import job completed,
        # which takes about a minute.
        import_job = client.wait_until_translation_memory_job_done(
            created.job_id, timeout_s=JOB_TIMEOUT_S
        )
        translation_memory_id = import_job.result.translation_memory_id
        assert import_job.operation == "import"
        assert import_job.ok
        assert translation_memory_id

        fetched = client.get_translation_memory(translation_memory_id)
        assert fetched.translation_memory_id == translation_memory_id
        assert fetched.name == name

        assert _is_listed(client, translation_memory_id)

        segments = client.list_translation_memory_segments(
            translation_memory_id
        )
        assert segments.segments
        assert segments.segments[0].source_segment_id

        exported = client.create_translation_memory_export(
            translation_memory_id
        )
        assert exported.job_id
        export_job = client.wait_until_translation_memory_job_done(
            exported.job_id, timeout_s=JOB_TIMEOUT_S
        )
        output = io.BytesIO()
        client.download_translation_memory_export(export_job, output)
        assert b"<tmx" in output.getvalue()
    finally:
        if translation_memory_id is not None:
            client.delete_translation_memory(translation_memory_id)


def _is_listed(client, translation_memory_id):
    for page in range(20):
        memories = client.list_translation_memories(page=page, page_size=100)
        if translation_memory_id in [
            memory.translation_memory_id for memory in memories
        ]:
            return True
        if not memories:
            return False
    return False
