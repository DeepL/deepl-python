# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Added support for using multiple glossaries via the `glossary_ids` parameter
  (up to 5 glossaries) in `translate_text()`, `translate_document()`,
  `translate_document_upload()`, and `translate_document_from_filepath()`.
- Added support for style rules in document translation via the `style_rule`
  parameter in `translate_document()`, `translate_document_upload()`, and
  `translate_document_from_filepath()`.
- Added support for translation memories in document translation via the
  `translation_memory` and `translation_memory_threshold` parameters in
  `translate_document()`, `translate_document_upload()`, and
  `translate_document_from_filepath()`.
- Added `--glossary-ids` CLI argument for the `text` and `document` commands,
  allowing up to 5 glossaries to be used per translation.
- Added `--style-id`, `--translation-memory-id`, and
  `--translation-memory-threshold` CLI arguments to the `document` command.

## [1.30.0] - 2026-04-09
### Added
- Added support for translation memories in text translation via
  `translation_memory` and `translation_memory_threshold` parameters in
  `translate_text()`.
- Added `list_translation_memories()` method to the `DeepLClient` class for
  listing available translation memories.
- Added `--translation-memory-id` and `--translation-memory-threshold` CLI
  arguments.

### Fixed
- Fixed "gitlab release" CI job to explicitly set the release-cli image, avoiding issues with missing `$HOME` from the global image.

## [1.29.0] - 2026-03-26
### Added
- Added new language constants from January 2026 API release of 81 new languages.
- Added support for style rules CRUD endpoints in the `DeepLClient` class:
  `create_style_rule()`, `get_style_rule()`, `update_style_rule_name()`,
  `update_style_rule_configured_rules()`, and `delete_style_rule()`.
- Added support for style rule custom instruction CRUD endpoints in the
  `DeepLClient` class: `create_style_rule_custom_instruction()`,
  `get_style_rule_custom_instruction()`,
  `update_style_rule_custom_instruction()`, and
  `delete_style_rule_custom_instruction()`.
  Please refer to the README for usage instructions.

### Changed
- Updated formality tests to accept either formal or informal output when using default formality,
  since the default formality is automatic.

## [1.28.0] - 2026-02-05
### Changed
- Updated three tests to be less flakey and reflect new behavior regarding the model type.
- Improved `NotFoundException` error message by removing the misleading "check server_url" suggestion.

### Fixed
- Fixed a bug where translating with style rules would sometimes incorrectly result in
  a "target_lang must match style rule language" error

### Security
- Updated dependencies to fix CVE-2025-66418 and CVE-2025-66471

## [1.27.0] - 2025-12-10
### Added
- Added `tag_handling_version` parameter to `translate_text()` to specify which version
  of the tag handling algorithm to use. Options are `v1` and `v2`.
- Added an example CLI script for realtime audio translation using DeepL's Voice API.

## [1.26.0] - 2025-12-03
### Added
- Added `custom_instructions` parameter to `translate_text()` to customize translation
  behavior with up to 10 instructions (max 300 characters each). Only supported for
  target languages: `de`, `en`, `es`, `fr`, `it`, `ja`, `ko`, `zh` and their variants.
  Note: using the `custom_instructions` parameter will use the `quality_optimized` model
  type as the default. Requests combining `custom_instructions` and the
  `latency_optimized` model type will be rejected.

### Fixed
- Fixed the cleanup of multilingual glossaries in the test suite where glossaries
  were not properly deleted after the test execution

## [1.25.0] - 2025-11-12
### Added
- Added support for the `GET /v3/style_rules` endpoint in the client library, the
  implementation can be found in the `DeepLClient` class. Please refer to the
  README for usage instructions
- Added `style_id` option to `translate_text()` which allows text translation with
  style rules.

## [1.24.0] - 2025-11-04
### Changed
- `extra_body_parameters` will now overwrite already set HTTP parameters

## [1.23.0] - 2025-09-30
### Added
- Added feature to add arbitrary body parameters in `translate_text`

### Deprecated
- Dropped support for Python 3.8 and older.

### Security
- Updated `requests` minimum version to 2.32.4 to resolve security advisories
  CVE-2024-47081 and CVE-2024-35195.

## [1.22.0] - 2025-04-30
### Added
- Added support for the /v3 Glossary APIs in the client library while providing backwards
  compatability for the previous /v2 Glossary endpoints. Please refer to the README for
  usage instructions.

## [1.21.1] - 2025-03-12
### Added
- (beta) optional parameter to specify timeout for document translation calls

## [1.21.0] - 2025-01-15
### Added
- Added support for the Write API in the client library, the implementation
  can be found in the `DeepLClient` class. Please refer to the README for usage
  instructions.

### Changed
- The main functionality of the library is now also exposed via the `DeepLClient`
  class. Please change your code to use this over the `Translator` class whenever
  convenient.

## [1.20.0] - 2024-11-15
### Added
- Added `model_type` option to `translate_text()` to use models with higher
  translation quality (available for some language pairs), or better latency.
  Options are `'quality_optimized'`, `'latency_optimized'`, and  `'prefer_quality_optimized'`
- Added the `model_type_used` field to `translate_text()` response, that
  indicates the translation model used when the `model_type` option is
  specified.

## [1.19.1] - 2024-09-17
### Fixed
- Fixed typing issues, black-formatting and a test case failure.

## [1.19.0] - 2024-09-17
### Added
- Added `billed_characters` to response from `translate_text()`.

## [1.18.0] - 2024-04-26
### Added
- New language available: Arabic (`'ar'`). Add language code constants and tests.
  Arabic is currently supported only for text translation; document translation
  support for Arabic is coming soon.

  Note: older library versions also support the new language, this update only adds new code constants.
- Added a section in the readme on how to configure retry options in `http_client.py`

## [1.17.0] - 2024-02-06
### Added
- Added `output_format` parameter for document upload function, that indicates
  the file extension of the desired file format for the translated document.
- Added basic usage example of the library

### Fixed
- Fixed typechecking errors when using `mypy`'s `strict` mode
  * Thanks to [derlikh-smart](https://github.com/derlikh-smart) and [vad](https://github.com/vad)
    for the report in [#82](https://github.com/DeepLcom/deepl-python/issues/82)

## [1.16.1] - 2023-11-07
### Fixed
- Fixed typo in error message when no auth key is provided.
- Removed dependency on `packaging` by replacing version comparison.

## [1.16.0] - 2023-11-03
### Added
- Add optional `context` parameter for text translation, that specifies
  additional context to influence translations, that is not translated itself.

### Changed
- Added notice in Readme that starting in 2024 the library will drop support for
  Python versions that are officially end-of-life.
- DeepL API calls now send requests with JSON-encoded bodies where possible.

### Fixed
- Catch failures while constructing the user agent string.
- Added `py.typed` to the package so that our package is typed for our users.
- Fixed most type errors in the package.

## [1.15.0] - 2023-06-09
### Fixed
- Removed `CHANGELOG.md` and `SECURITY.md` from the python package. The `LICENSE` file is no longer installed, but still included in package tarball and wheel files.
  * Thanks to [TurtleWilly](https://github.com/TurtleWilly) for the report in [#66](https://github.com/DeepLcom/deepl-python/issues/66).
- Fix a dependency error in our CI by updating to a higher poetry version in most cases.
- Fix getUsage request to be a HTTP GET request, not POST.
- Change document translation to poll the server every 5 seconds. This should greatly reduce observed document translation processing time.

## [1.14.0] - 2023-02-21
### Added
- Add [example](examples/json) to translate JSON inputs.
- Added platform and python version information to the user-agent string that is sent with API calls, along with an opt-out.
- Added method for applications that use this library to identify themselves in API requests they make.
- Added `verify_ssl` option to `Translator` to control underlying `requests` session.
  * Thanks to [andrefloriani](https://github.com/andrefloriani) for the
    suggestion in [#60](https://github.com/DeepLcom/deepl-python/issues/60).

## [1.13.0] - 2023-01-26
### Added
- Add [example script](examples/mustache) to translate Mustache templates.
- Add support for storing your API Key in a keyring via the `keyring` module.
- Added a CI check for copyright headers.
- New languages available: Korean (`'ko'`) and Norwegian (bokmål) (`'nb'`). Add language code constants and tests.

  Note: older library versions also support the new languages, this update only adds new code constants.

### Fixed
- Copyright headers are updated for 2023

### Security
- Update `certifi` to resolve security advisory.
  * `certifi` is a development-only dependency; library users are unaffected.

## [1.12.0] - 2023-01-09
### Added
- State explicitly that this library supports Python 3.11.
- Added the `should_retry` and `http_status_code` properties to all exceptions
  thrown by the library.

### Fixed
- Fix `py` dependency by upgrading `pytest` version to 7.2.0 for Python 3.7+.
  For Python 3.6 tests `pytest` needs to be added manually.
- Remove unused `tox` dependency.
- Update `coverage` dependency.
- Also send options in API requests even if they are default values.

## [1.11.0] - 2022-09-26
### Added
- Add formality options `PREFER_LESS` and `PREFER_MORE`.

### Changed
- Requests resulting in `503 Service Unavailable` errors are now retried.
  Attempting to download a document before translation is completed will now
  wait and retry (up to 5 times by default), rather than raising an exception.

## [1.10.0] - 2022-09-09
### Added
- New language available: Ukrainian (`'uk'`). Add language code constant and tests.

  Note: older library versions also support new languages, this update only adds new code constant.

### Changed
- Add note and workaround to README about Poetry error on Ubuntu 22.04.
  * Pull request [#48](https://github.com/DeepLcom/deepl-python/pull/48)
    thanks to [FOehlschlaeger](https://github.com/FOehlschlaeger).

## [1.9.0] - 2022-07-07
### Added
- Add `Translator.create_glossary_from_csv()` allowing glossaries downloaded
  from website to be easily uploaded to API.

## [1.8.0] - 2022-06-10
### Added
- Optional `filename` parameter added to `Translator.translate_document()`, only
  required if uploading string or bytes containing file content.
  * Pull request [#30](https://github.com/DeepLcom/deepl-python/pull/30)
    thanks to [seratch](https://github.com/seratch).

### Changed
- Update contributing guidelines, we can now accept Pull Requests.

### Fixed
- Fix GitLab CI config.

## [1.7.0] - 2022-05-18
### Added
- New languages available: Indonesian (`'id'`) and Turkish (`'tr'`). Add language code constants and tests.

  Note: older library versions also support the new languages, this update only adds new code constants.
- Add `limit_reached` and `any_limit_reached` properties to `Usage` object
  returned by `get_usage()`.
- Add `Translator.translate_document_wait_until_done()` to poll translation
  status until translation is complete or fails.
- Add `auth_key_is_free_account()` utility function.

### Changed
- Improve readme usage examples.

### Deprecated
- Deprecate `limit_exceeded` and `any_limit_exceeded` properties of `Usage`
  object returned by `get_usage()`, use `limit_reached` and `any_limit_reached`
  instead.

## [1.6.0] - 2022-04-12
### Added
- Add `error_message` property to `DocumentStatus`, describing the error in case of document translation failure.

### Changed
- Improve error message if `translate_text_with_glossary` is called without an instance of `GlossaryInfo`.
- `translate_document` and `translate_document_from_filepath` return final `DocumentStatus`, allowing the number of
  billed characters to be queried.

## [1.5.1] - 2022-04-11
### Fixed
- Fix bug in CLI languages command causing some target languages to be omitted.
- Fix some tests that intermittently failed.

## [1.5.0] - 2022-02-28
### Added
- Add support for HTML tag handling in `translate_text()`.

### Deprecated
- `DocumentTranslationException.document_request` is deprecated, use `document_handle` instead.

## [1.4.1] - 2022-02-04
### Fixed
- Fix bug in `DocumentTranslationException` stringize function.

## [1.4.0] - 2022-01-19
### Added
- Add contribution guidelines -- currently we are unable to accept Pull Requests.
- Add `--glossary-id` argument for CLI document command.

### Changed
- Improve README.
- Raise `DocumentNotReadyException` when attempting to download a document before it has been translated. Previously the
  base class `DeepLException` was thrown.

### Fixed
- Add optional filename argument to `translate_document_upload()` to fix uploading file content as string or bytes.

## [1.3.1] - 2021-11-15
### Changed
- Limit document status update wait time to 60 seconds, and log wait times.

## [1.3.0] - 2021-11-15
Note: the PyPI package for 1.3.0 included changes from 1.3.1, so it has been yanked.

### Added
- Add glossary support for document translation.
- Add proxy support.

### Fixed
- Fix issues with parallelized tests by changing how test glossaries are created and deleted.

## [1.2.1] - 2021-10-19
### Added
- Add support for Python 3.10.

### Fixed
- Fix bug that caused User-Agent header to be omitted from HTTP requests.
- Fix glossary name prefix used in unit-tests to match git repository name.
- Add workaround for possible issue in datetime.strptime in Python 3.6.

## [1.2.0] - 2021-10-07
### Added
- Add `Translator.get_glossary_languages()` to query language pairs supported for glossaries.
- Add constants for all supported languages codes, for example: `Language.GERMAN`.

### Changed
- Internal language caching and client-side checking of language codes are removed.

### Deprecated
- Some optional arguments related to language caching are now deprecated, and will be removed in a future version:
  * `Translator()`: the `skip_language_check` argument
  * `Translator.get_source_languages()` and `Translator.get_target_languages()`: the `skip_cache` argument

### Fixed
- Fix HTTP request retries for document uploads.

## [1.1.3] - 2021-09-27
### Changed
- Loosen requirement for requests to 2.0 or higher.

## [1.1.2] - 2021-09-21
### Changed
- Improve request exception messages and include exception stacktraces.
- Update unit tests for server error message changes.

## [1.1.1] - 2021-09-13
### Fixed
- Fix typing.List issue on Python 3.6.
- Add workaround for datetime.strptime bug in Python 3.6.

## [1.1.0] - 2021-09-13
### Added
- Add security policy.
- Add support for glossary API functions.

### Fixed
- README and comments improvements, type hints and other minor fixes.

## [1.0.1] - 2021-08-13
### Added
- Add explicit copyright notice to all source files.

### Fixed
- Force response encoding to UTF-8 to avoid issues with older versions of requests package.

## [1.0.0] - 2021-08-12
### Changed
- All API calls use Authorization header instead of auth_key parameter.

## [0.4.1] - 2021-08-10
### Changed
- Minor updates to pyproject.toml and README.md.

## [0.4.0] - 2021-08-05
Version increased to avoid conflicts with old packages on PyPI.

## [0.3.0] - 2021-08-05
### Added
- Package uploaded to PyPI. Thanks to [Adrian Freund](mailto:mail@freundtech.com) for transferring the deepl package
  name.
- Clarify minimum version of requests module to 2.18.

## [0.2.0] - 2021-07-28
### Changed
- Improve exception hierarchy.
- Translator() server_url argument works with and without trailing slash.
- Translator.translate_text() accepts a single text argument, which may be a list or other iterable.

### Fixed
- Fix examples in readme to match function interface changes.

## [0.1.0] - 2021-07-26
Initial version.

[Unreleased]: https://github.com/DeepLcom/deepl-python/compare/v1.30.0...HEAD
[1.30.0]: https://github.com/DeepLcom/deepl-python/compare/v1.29.0...v1.30.0
[1.29.0]: https://github.com/DeepLcom/deepl-python/compare/v1.28.0...v1.29.0
[1.28.0]: https://github.com/DeepLcom/deepl-python/compare/v1.27.0...v1.28.0
[1.27.0]: https://github.com/DeepLcom/deepl-python/compare/v1.26.0...v1.27.0
[1.26.0]: https://github.com/DeepLcom/deepl-python/compare/v1.25.0...v1.26.0
[1.25.0]: https://github.com/DeepLcom/deepl-python/compare/v1.24.0...v1.25.0
[1.24.0]: https://github.com/DeepLcom/deepl-python/compare/v1.23.0...v1.24.0
[1.23.0]: https://github.com/DeepLcom/deepl-python/compare/v1.22.0...v1.23.0
[1.22.0]: https://github.com/DeepLcom/deepl-python/compare/v1.21.1...v1.22.0
[1.21.1]: https://github.com/DeepLcom/deepl-python/compare/v1.21.0...v1.21.1
[1.21.0]: https://github.com/DeepLcom/deepl-python/compare/v1.20.0...v1.21.0
[1.20.0]: https://github.com/DeepLcom/deepl-python/compare/v1.19.1...v1.20.0
[1.19.1]: https://github.com/DeepLcom/deepl-python/compare/v1.19.0...v1.19.1
[1.19.0]: https://github.com/DeepLcom/deepl-python/compare/v1.18.0...v1.19.0
[1.18.0]: https://github.com/DeepLcom/deepl-python/compare/v1.17.0...v1.18.0
[1.17.0]: https://github.com/DeepLcom/deepl-python/compare/v1.16.1...v1.17.0
[1.16.1]: https://github.com/DeepLcom/deepl-python/compare/v1.16.0...v1.16.1
[1.16.0]: https://github.com/DeepLcom/deepl-python/compare/v1.15.0...v1.16.0
[1.15.0]: https://github.com/DeepLcom/deepl-python/compare/v1.14.0...v1.15.0
[1.14.0]: https://github.com/DeepLcom/deepl-python/compare/v1.13.0...v1.14.0
[1.13.0]: https://github.com/DeepLcom/deepl-python/compare/v1.12.0...v1.13.0
[1.12.0]: https://github.com/DeepLcom/deepl-python/compare/v1.11.0...v1.12.0
[1.11.0]: https://github.com/DeepLcom/deepl-python/compare/v1.10.0...v1.11.0
[1.10.0]: https://github.com/DeepLcom/deepl-python/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/DeepLcom/deepl-python/compare/v1.8.0...v1.9.0
[1.8.0]: https://github.com/DeepLcom/deepl-python/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/DeepLcom/deepl-python/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/DeepLcom/deepl-python/compare/v1.5.1...v1.6.0
[1.5.1]: https://github.com/DeepLcom/deepl-python/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/DeepLcom/deepl-python/compare/v1.4.1...v1.5.0
[1.4.1]: https://github.com/DeepLcom/deepl-python/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/DeepLcom/deepl-python/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/DeepLcom/deepl-python/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/DeepLcom/deepl-python/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/DeepLcom/deepl-python/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/DeepLcom/deepl-python/compare/v1.1.3...v1.2.0
[1.1.3]: https://github.com/DeepLcom/deepl-python/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/DeepLcom/deepl-python/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/DeepLcom/deepl-python/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/DeepLcom/deepl-python/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/DeepLcom/deepl-python/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/DeepLcom/deepl-python/compare/v0.4.1...v1.0.0
[0.4.1]: https://github.com/DeepLcom/deepl-python/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/DeepLcom/deepl-python/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/DeepLcom/deepl-python/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/DeepLcom/deepl-python/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/DeepLcom/deepl-python/releases/tag/v0.1.0
