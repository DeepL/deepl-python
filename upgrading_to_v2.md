# Upgrading to 2.0.0

Version 2.0.0 removes everything that was deprecated in 1.x, makes several
functions stricter about invalid input, and changes how failed requests and
retries are reported. Read the [quick checklist](#quick-checklist) first: most
projects only need the first few items. The minimum supported Python version
is unchanged, so the upgrade does not require a new interpreter.

For the move from monolingual to multilingual glossaries, see
[upgrading_to_multilingual_glossaries.md](upgrading_to_multilingual_glossaries.md).

## Requirements

- Python 3.9 or later (`>=3.9,<4`), as in 1.33.0. The library is tested with
  Python 3.9 to 3.15.
- Runtime dependencies are unchanged: `requests>=2.32.5`, and the optional
  `keyring` for the command line tool.
- The package still ships type information (`py.typed`); run your type checker
  again, as several annotations changed (see [Types and
  signatures](#types-and-signatures)).

## Quick checklist

1. Replace `deepl.Translator` with `deepl.DeepLClient`: [Client and options](#client-and-options).
2. Replace `Language.GERMAN` and the other language constants with strings such as `"de"`: [Client and options](#client-and-options).
3. Replace `translate_text_with_glossary()` with `translate_text(..., glossary=...)`: [Glossaries](#glossaries).
4. Rename deprecated keyword arguments (`glossary_dicts`, `glossary_dict`, `csv_data`, `glossary_id`, `input_file`, `style`): [Glossaries](#glossaries), [Translation memories](#translation-memories), [Text translation](#text-translation).
5. Pass `output_file` to `translate_document_download()` and `download_translation_memory_export()`; they no longer return a response: [Documents](#documents).
6. Catch `NotFoundException` instead of `GlossaryNotFoundException`: [Glossaries](#glossaries).
7. Read usage through `any_character_limit_reached` and `is not None` checks: [Usage](#usage).
8. Replace the `deepl.http_client` module settings with client options: [Client and options](#client-and-options).
9. Update `except` clauses around document and translation memory helpers, which now raise different exceptions: [Documents](#documents), [Translation memories](#translation-memories).
10. Expect `ValueError` for empty texts and language codes, and no retries after a request that may have reached the server: [Errors, validation and retries](#errors-validation-and-retries).

## Client and options

### `Translator` is removed

`DeepLClient` takes the same constructor arguments, except the removed
`skip_language_check` (see [Removed arguments without
effect](#removed-arguments-without-effect)), and has every function
`Translator` had, except `translate_text_with_glossary()` (see
[Glossaries](#glossaries)). `DeepLClient` no longer extends `Translator`, so
`isinstance(client, deepl.Translator)` and `Translator` annotations must use
`DeepLClient`.

```python
# Before
translator = deepl.Translator(auth_key)

# After
client = deepl.DeepLClient(auth_key)
```

The module `deepl.translator` is gone. Import exceptions from `deepl` or
`deepl.exceptions`, and result and option types (`TextResult`,
`DocumentHandle`, `Usage`, `Formality`, ...) from `deepl` or `deepl.api_data`.

```python
# Before
from deepl.translator import TextResult, QuotaExceededException

# After
from deepl import TextResult, QuotaExceededException
```

### Language code constants are removed

`Language.GERMAN`, `Language.ENGLISH_AMERICAN` and the other code constants are
removed. Pass codes as strings, or use the codes returned by
`get_source_languages()` and `get_target_languages()`. The `Language` class
remains as the type of those results.

```python
# Before
client.translate_text("Hello", target_lang=deepl.Language.GERMAN)

# After
client.translate_text("Hello", target_lang="de")
```

### Module-level HTTP settings are removed

The module `deepl.http_client` is now the internal `deepl._http_client`.
`HttpClient`, `read_response_text()` and `iter_response_content()` are no
longer public, and the settings `max_network_retries`, `min_connection_timeout`
and `user_agent` no longer exist. Use client options instead.

```python
# Before
import deepl.http_client
deepl.http_client.max_network_retries = 3
deepl.http_client.min_connection_timeout = 20.0
deepl.http_client.user_agent = "my-app/1.0"

# After
client = deepl.DeepLClient(
    auth_key,
    max_retries=3,
    timeout_s=20.0,
    headers={"User-Agent": "my-app/1.0"},
)
```

`max_retries` and `timeout_s` default to `5` and `10.0` for every client;
`None` also selects these defaults. Clients no longer read any module-level
setting, so pass the options to every client that needs other values.

### Removed arguments without effect

`DeepLClient(skip_language_check=...)` and the `skip_cache` argument of
`get_source_languages()` and `get_target_languages()` are removed. They had no
effect; delete them from calls.

### Constructor validation

`DeepLClient` and `DeepLAdminClient` raise `ValueError` when the constructor
is called with a `proxy` URL that has no host or a scheme other than `http`,
`https`, `socks4`, `socks4a`, `socks5` or `socks5h`, or with a `server_url`
that is not an absolute `http` or `https` URL with a host. Before, the first
request failed. A proxy URL without a scheme is still used as `http://`.

The type of `proxy` is no longer checked: a value that is neither a string nor
a dictionary raises Python's own error (`AttributeError` for a list) instead of
`ValueError`.

### `send_platform_info=None`

`send_platform_info=None` sends the platform information in the User-Agent, as
when the option is omitted. Before, it sent only the library version. Pass
`False` to opt out.

### Free account check

`auth_key_is_free_account()` (in `deepl` and `deepl.util`) is removed. Use
`is_free_account_auth_key()`, which also ignores leading and trailing
whitespace.

## Text translation

- `rephrase_text()`: the `style` keyword is removed; use `writing_style`.
- `SplitSentences.DEFAULT` is removed; use `SplitSentences.ALL`, which it
  aliased.
- `translate_text()`, `rephrase_text()` and `correct_text()` raise
  `ValueError` for an empty string in a list of texts (see [Errors,
  validation and retries](#errors-validation-and-retries)).
- `translate_text()`, `rephrase_text()` and `correct_text()` no longer check
  the type of `text`. A value that is neither a string nor iterable raises
  Python's own `TypeError` from `list()` instead of `TypeError: text parameter
  must be a string or an iterable of strings`.
- `rephrase_text()` sends `writing_style` and `tone` whenever they are not
  `None`. An empty string was silently dropped before; pass `None` to leave
  them unset.

```python
# Before
client.rephrase_text("hello", style="business")

# After
client.rephrase_text("hello", writing_style="business")
```

## Documents

### Downloads require `output_file`

`translate_document_download()` and `download_translation_memory_export()`
require `output_file` and return `None`. They no longer return the streaming
`requests.Response`. Pass a file object opened in binary mode.

```python
# Before
response = client.translate_document_download(handle)

# After
with open("out.docx", "wb") as output_file:
    client.translate_document_download(handle, output_file)
```

### Failed translations raise

`translate_document_wait_until_done()` raises `DeepLException` with the API's
error message when the translation fails. Before, it returned the
`DocumentStatus` with `ok` `False`.

```python
# Before
status = client.translate_document_wait_until_done(handle)
if not status.ok:
    ...

# After
try:
    status = client.translate_document_wait_until_done(handle)
except deepl.DeepLException as error:
    ...
```

### `translate_document()` and `translate_document_from_filepath()`

- A failed upload, and invalid arguments including a missing `target_lang`,
  raise `DocumentTranslationException` with `document_handle` `None`. It
  copies `http_status_code` and `should_retry`, and the original exception (for
  example `QuotaExceededException`) is its `__cause__`. Catch
  `DocumentTranslationException` instead of the upload exception.
- `translate_document_from_filepath()` raises `ValueError` instead of
  `FileNotFoundError` for a missing input file, and
  `DocumentTranslationException` instead of `OSError` if the input or output
  file cannot be opened.
- `translate_document_from_filepath()` no longer overwrites an existing
  `output_path`; it raises `DocumentTranslationException` before sending any
  request. Delete the file first if you want to replace it.
- `DocumentTranslationException.document_request` is removed; use
  `document_handle`.
- `DocumentStatus.Status.DOWNLOADED` is removed. The API does not return it; an
  unknown status is kept as a string.

### `translate_document_upload()` and `translate_document()`

- The given `filename` is sent as the upload's file name for a file object
  too. Before, it was used only for `str` or `bytes` content, and a file object
  was sent under its own name, or as `file` if it had none. The API detects the
  input format from the file name's extension. Without `filename`, a file
  object is still sent under its own name.
- `output_format` is sent whenever it is not `None`. An empty string was
  silently dropped before; pass `None` to leave it unset.

## Glossaries

### Removed functions

`translate_text_with_glossary()` is removed. Call `translate_text()` with the
`glossary` argument and the glossary's languages; for an `EN` glossary pass
`target_lang="EN-GB"` or `"EN-US"`.

```python
# Before
client.translate_text_with_glossary("Hello", glossary, target_lang="de")

# After
client.translate_text(
    "Hello",
    source_lang=glossary.source_lang,
    target_lang=glossary.target_lang,
    glossary=glossary,
)
```

`get_multilingual_glossary_entries()` is removed. Use
`get_multilingual_glossary_dictionary_entries()`, which returns the
`MultilingualGlossaryDictionaryEntries` directly. Its `entries` is a `dict`,
not a TSV string, so remove calls to `convert_tsv_to_dict()` on it.
`MultilingualGlossaryDictionaryEntriesResponse`, the return type of the
removed function, is removed too.

```python
# Before
response = client.get_multilingual_glossary_entries(glossary, "en", "de")
entries = deepl.convert_tsv_to_dict(response.dictionaries[0].entries)

# After
entries = client.get_multilingual_glossary_dictionary_entries(
    glossary, "en", "de"
).entries
```

### Renamed keyword arguments

The deprecated names are removed from the multilingual glossary functions.

| Before         | After          |
|----------------|----------------|
| `glossary_dicts` | `dictionaries` |
| `glossary_dict`  | `dictionary`   |
| `csv_data`       | `csv`          |
| `glossary_id`    | `glossary`     |

```python
# Before
client.create_multilingual_glossary("Name", glossary_dicts=dictionaries)

# After
client.create_multilingual_glossary("Name", dictionaries=dictionaries)
```

### `delete_multilingual_glossary_dictionary()`

The signature is `(glossary, source_lang, target_lang, *, dictionary=None)`.
The `dictionary` argument is keyword-only.

```python
# Before
client.delete_multilingual_glossary_dictionary(glossary, dictionary)

# After
client.delete_multilingual_glossary_dictionary(glossary, dictionary=dictionary)
```

### `GlossaryNotFoundException` is removed

Every glossary function raises `NotFoundException` for HTTP 404, with the
message `Not found` instead of `Glossary not found`.
`get_multilingual_glossary_dictionary_entries()` also raises it if the glossary
has no dictionary for the language pair.

```python
# Before
except deepl.GlossaryNotFoundException:

# After
except deepl.NotFoundException:
```

### Behaviour

- `create_multilingual_glossary()` raises `ValueError` if `dictionaries` is
  empty, and the `update_` and `replace_` `..._dictionary_from_csv()` functions
  raise it for empty CSV content. Before, an empty dictionary was sent.
- Multilingual glossary functions accept dictionaries read from the API, and a
  `MultilingualGlossaryDictionaryEntries` whose `entries` is a TSV string; they
  no longer raise `AttributeError`.
- `update_multilingual_glossary_dictionary()` and
  `replace_multilingual_glossary_dictionary()` no longer check `dictionary` for
  `None`. `None` raises Python's own `AttributeError`, still before any
  request, instead of `TypeError: ... missing required argument: dictionary`.
- `create_glossary_from_csv()` and the multilingual glossary `*_from_csv()`
  functions no longer check the type of what a file-like `csv_data` / `csv`
  returns from `read()`. `create_glossary_from_csv()` sends it as the entries,
  and the multilingual functions pass it to the CSV parser, which raises
  Python's own `TypeError` for a non-iterable. Before, a result that was
  neither `str` nor `bytes` raised `ValueError: Entries of the glossary are
  invalid`.

## Style rules

- `ConfiguredRules` is removed. `StyleRuleInfo.configured_rules` is a plain
  `dict` mapping category names to dicts of rule names and values, the same
  shape `create_style_rule()` and `update_style_rule_configured_rules()` take.
  Categories the library does not know are kept, and `{}` from the API stays
  `{}`; `None` means the response omitted the field.
- `StyleRuleInfo.custom_instructions` is `None` instead of `[]` when the
  response omits the field, for example for `get_all_style_rules()` without
  `detailed=True`. Check for `None` before iterating.
- `CustomInstruction.id` is a required keyword-only `str`. Code that builds
  `CustomInstruction` objects must pass `id=`; a response without `id` raises
  `DeepLException`.

```python
# Before
numbers = rule.configured_rules.numbers

# After
numbers = (rule.configured_rules or {}).get("numbers", {})
```

## Translation memories

- `upload_translation_memory_file()`: the `input_file` keyword is removed; use
  `content`, which is required.
- `wait_until_translation_memory_job_done()` raises `DeepLException` with the
  API's error message when the job fails or expires, instead of returning the
  job with `ok` `False`.
- `TranslationMemoryJob.done` and `TranslationMemoryJobResult.done` are `True`
  only for a completed job. Use `ok` to detect failure.
  `TranslationMemoryJobResult.STATUS_DOWNLOADED` is removed.
- `import_translation_memory_from_filepath()` and
  `export_translation_memory_to_filepath()` raise the new
  `TranslationMemoryJobException` (a `DeepLException`) for every failure except
  a missing input file, which raises `ValueError`. The underlying exception is
  its `__cause__`; it also has `job_id` and `job`. Catch it instead of
  `OSError`, `FileNotFoundError`, `PermissionError` or
  `QuotaExceededException`. `export_translation_memory_to_filepath()` no longer
  overwrites an existing `output_path`.
- `download_translation_memory_export()` raises `DeepLException` instead of
  `ValueError` if the job has no download URL.
- `TranslationMemoryJob` requires `creation_time` and `updated_time` as
  `datetime.datetime`, placed after `results`; a response without them raises
  `DeepLException`.

```python
# Before
try:
    client.export_translation_memory_to_filepath(tm, "out.tmx")
except OSError:
    ...

# After
try:
    client.export_translation_memory_to_filepath(tm, "out.tmx")
except deepl.TranslationMemoryJobException as error:
    ...
```

## Usage

- `Usage.any_limit_reached` and `Usage.any_limit_exceeded` are removed; use
  `Usage.any_character_limit_reached`, which is `True` if `character` or
  `api_key_character` reached its limit. The speech minutes are not considered.
- `Usage.Detail.limit_exceeded` is removed; use `limit_reached`.
  `Usage.Detail.valid` is removed; an absent usage type is `None`.
- `Usage.document` and `Usage.team_document` are removed, as the API no longer
  returns document usage.
- `Usage.character` and `Usage.api_key_character` are `None` unless the
  response has both count and limit.

```python
# Before
usage = client.get_usage()
if usage.document.valid and usage.document.limit_exceeded:
    ...

# After
usage = client.get_usage()
if usage.any_character_limit_reached:
    ...
```

## Errors, validation and retries

- Functions that create a resource are retried only when the request was not
  sent: after HTTP 429 or a network failure while connecting, before any
  request byte is written, such as a DNS failure, a refused connection, a
  connect timeout, or a reset or timeout in the TLS or proxy handshake. They are not retried after HTTP 5xx, a read timeout, a reset
  connection or a response body cut off mid-read, because that could create the
  resource twice. This covers the `create_*` glossary, spoken terms, style
  rule, style profile and translation memory import and export functions, the
  document upload of `translate_document*()`, and
  `DeepLAdminClient.create_developer_key()`.
- For those functions, `should_retry` on the raised exception is `True` only
  after HTTP 429, a network failure while connecting (see the previous item)
  or a body cut off mid-read. After HTTP 5xx, a read timeout, a reset connection or
  a broken pipe it is `False`. If you retry yourself, check for duplicates
  first.
- A connection that breaks while a streamed body is read
  (`translate_document_download()`, `download_translation_memory_export()`)
  raises `ConnectionException` with `should_retry` `True`, not `False`. It is
  still not retried automatically, because `output_file` may be partly written.
- A failure to connect to the proxy (a DNS failure, a refused connection or a
  connect timeout) is retried and raises `ConnectionException` with
  `should_retry` `True`, like the same failure without a proxy. Before, every
  proxy failure raised `ConnectionException` with `should_retry` `False` at
  once. An error answer from the proxy to `CONNECT` (such as 407) and a TLS
  failure with an `https://` proxy are still not retried.
- These calls raise `ValueError` before sending any request: an empty string in
  a list passed to `translate_text()`, `rephrase_text()` or `correct_text()`;
  an empty `target_lang`, or a given empty `source_lang`; an empty
  `target_lang` in `rephrase_text()` and `correct_text()` (pass `None` or omit
  it to keep the input language); and an empty ID or a `SpokenTerms` without
  ID in `get_spoken_terms()`, `update_spoken_terms()`, `delete_spoken_terms()`,
  `get_spoken_terms_entries()`, `replace_spoken_terms_list()` and
  `delete_spoken_terms_list()`.
- `translate_text()`, `translate_document_upload()` and the document functions
  that call it also raise `ValueError` before any request if `glossary`, an
  entry of `glossary_ids`, `style_rule`, `style_profile` or
  `translation_memory` is an empty string or an object with an empty ID.
  Before, the empty ID was sent to the API.
- The multilingual glossary functions, the spoken terms functions and the
  custom instruction functions of style rules (`create_style_rule()`,
  `create_style_rule_custom_instruction()`,
  `update_style_rule_custom_instruction()`) raise `ValueError` before any
  request if a required language is empty, or an optional `source_language`
  is an empty string. Before, the empty value was sent.

## Types and signatures

- `dictionaries`, `dictionary`, `csv` (multilingual glossary functions),
  `glossary` of `get_multilingual_glossary()` and `content` of
  `upload_translation_memory_file()` are no longer `Optional`.
- `Usage.Detail(count, limit)` takes two `int` values; the former
  `(json, prefix)` constructor is gone.
- The `timeout_s` of the document and translation memory wait functions is
  annotated `Optional[float]`; no runtime change.
- `deepl` now exports all public types of `deepl.api_data`, including
  `WritingStyle`, `WritingTone`, `WriteResult`, `StyleRuleInfo`,
  `CustomInstruction`, the translation memory types and `ModelType`.
  `deepl.WritingStyle` used to raise `AttributeError`.

## Internal classes

These are internals that were reachable from the public package and changed or
were removed:

- `ConfiguredRules` in `deepl.api_data`.
- `Usage.Detail.__init__(json, prefix)`, now `Usage.Detail(count, limit)`.
