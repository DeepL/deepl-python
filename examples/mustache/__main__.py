# Copyright 2023 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.

import argparse
import deepl
import os

from mustache import translate_mustache


env_auth_key = "DEEPL_AUTH_KEY"
env_server_url = "DEEPL_SERVER_URL"


def get_parser(prog_name):
    """Constructs and returns the argument parser."""
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="Translate Mustache templates using the DeepL API "
        "(https://www.deepl.com/docs-api).",
        epilog="If you encounter issues while using this example, please "
        "report them at https://github.com/DeepLcom/deepl-python/issues",
    )

    parser.add_argument(
        "--auth-key",
        default=None,
        help="authentication key as given in your DeepL account; the "
        f"{env_auth_key} environment variable is used as secondary fallback",
    )
    parser.add_argument(
        "--server-url",
        default=None,
        metavar="URL",
        help=f"alternative server URL for testing; the {env_server_url} "
        f"environment variable may be used as secondary fallback",
    )
    parser.add_argument(
        "--to",
        "--target-lang",
        dest="target_lang",
        required=True,
        help="language into which the template should be translated",
    )
    parser.add_argument(
        "--from",
        "--source-lang",
        dest="source_lang",
        help="language of the template to be translated",
    )
    parser.add_argument(
        "template",
        nargs="+",
        type=str,
        help="template to be translated. Wrap template in quotes to prevent "
        "the shell from splitting on whitespace.",
    )

    return parser


def main():
    # Create a parser, reusing most of the arguments from the main CLI
    parser = get_parser(prog_name=None)
    args = parser.parse_args()
    auth_key = args.auth_key or os.getenv(env_auth_key)
    server_url = args.server_url or os.getenv(env_server_url)
    if auth_key is None:
        raise Exception(
            f"Please provide authentication key via the {env_auth_key} "
            "environment variable or --auth_key argument"
        )

    # Create a DeepLClient object, and call get_usage() to validate connection
    deepl_client = deepl.DeepLClient(auth_key, server_url=server_url)
    deepl_client.get_usage()

    for template in args.template:
        # Call translate_mustache() to translate the Mustache template
        output = translate_mustache(
            template,
            translator=deepl_client,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
        )
        print(output)


if __name__ == "__main__":
    main()
