# Copyright 2023 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import io
import deepl
import os

env_auth_key = "DEEPL_AUTH_KEY"
env_server_url = "DEEPL_SERVER_URL"


def main() -> None:
    auth_key = os.getenv(env_auth_key)
    server_url = os.getenv(env_server_url)
    if auth_key is None:
        raise Exception(
            f"Please provide authentication key via the {env_auth_key} "
            "environment variable or --auth_key argument"
        )

    # Create a Translator object, and call get_usage() to validate connection
    translator: deepl.Translator = deepl.Translator(
        auth_key, server_url=server_url
    )
    u: deepl.Usage = translator.get_usage()
    u.any_limit_reached

    # Use most translation features of the library
    _ = translator.translate_text(
        ["I am an example sentence", "I am another sentence"],
        source_lang="EN",
        target_lang="FR",
        formality=deepl.Formality.DEFAULT,
        tag_handling=None,
    )
    ginfo: deepl.GlossaryInfo = translator.create_glossary(
        "Test Glossary", "DE", "FR", {"Hallo": "Bonjour"}
    )
    with io.BytesIO() as output_file:
        doc_status: deepl.DocumentStatus = translator.translate_document(
            "My example document",
            output_file,
            source_lang="DE",
            target_lang="FR",
            filename="example.txt",
            glossary=ginfo,
        )
        doc_status.done
    _ = translator.translate_text_with_glossary(
        ["Ich bin ein Beispielsatz.", "Ich bin noch ein Satz."], glossary=ginfo
    )

    print("Success")

    # cleanup
    translator.delete_glossary(ginfo.glossary_id)


if __name__ == "__main__":
    main()
