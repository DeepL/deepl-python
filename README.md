# DeepL Python Library

[![PyPI version](https://img.shields.io/pypi/v/deepl.svg)](https://pypi.org/project/deepl/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/deepl.svg)](https://pypi.org/project/deepl/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blueviolet.svg)](https://github.com/DeepLcom/deepl-python/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/deepl)](https://pypistats.org/packages/deepl)

The [DeepL API][api-docs] is a language AI API that allows other computer programs
to send texts and documents to DeepL's servers and receive high-quality
translations and improvements to the text. This opens a whole universe of
opportunities for developers: any translation product you can imagine can now
be built on top of DeepL's best-in-class translation technology.

The DeepL Python library offers a convenient way for applications written in
Python to interact with the DeepL API. We intend to support all API functions
with the library, though support for new features may be added to the library
after they’re added to the API.

## Getting an authentication key

To use the DeepL Python Library, you'll need an API authentication key. To get a
key, [please create an account here][create-account]. With a DeepL API Free
account you can consume up to 500,000 characters/month for free.

## Installation

The library can be installed from [PyPI][pypi-project] using pip:

```shell
pip install --upgrade deepl
```

If you need to modify this source code, install the dependencies using poetry:

```shell
poetry install
```

On Ubuntu 22.04 an error might occur: `ModuleNotFoundError: No module named 
'cachecontrol'`. Use the workaround `sudo apt install python3-cachecontrol` as
explained in this [bug report][bug-report-ubuntu-2204].

### Requirements

The library is tested with Python versions 3.9 to 3.13.

The `requests` module is used to perform HTTP requests; the minimum is version
2.32.4.

We periodically drop support for older Python versions that have
reached official end-of-life. You can find the Python versions and support
timelines [here][python-version-list].

## Usage

Import the package and construct a `DeepLClient`. The first argument is a string
containing your API authentication key as found in your
[DeepL Pro Account][pro-account].

Be careful not to expose your key, for example when sharing source code.

```python
import deepl

auth_key = "f63c02c5-f056-..."  # Replace with your key
deepl_client = deepl.DeepLClient(auth_key)

result = deepl_client.translate_text("Hello, world!", target_lang="FR")
print(result.text)  # "Bonjour, le monde !"
```

This example is for demonstration purposes only. In production code, the
authentication key should not be hard-coded, but instead fetched from a
configuration file or environment variable.

`DeepLClient` accepts additional options, see [Configuration](#configuration)
for more information.

The `Translator` class is deprecated: it receives no new features and will be
removed in the next major version. Creating a `Translator` emits a
`DeprecationWarning`. `DeepLClient` supports all of its functions, so replace
`deepl.Translator(...)` with `deepl.DeepLClient(...)`.

`deepl.is_free_account_auth_key(auth_key)` returns `True` if the key belongs
to a DeepL API Free account (it ends with `:fx`). `auth_key_is_free_account()`
is deprecated in its favour. Leading and trailing whitespace of the key is
ignored.

### Translating text

To translate text, call `translate_text()`. The first argument is a string
containing the text you want to translate, or a list of strings if you want to
translate multiple texts.

`source_lang` and `target_lang` specify the source and target language codes
respectively. The `source_lang` is optional, if it is unspecified (or `None`)
the source language will be auto-detected. Both may be passed as keyword
arguments or positionally after the text, for example
`translate_text("Hello", None, "FR")`.

Language codes are **case-insensitive** strings according to ISO 639-1, for
example `'DE'`, `'FR'`, `'JA''`. Some target languages also include the regional
variant according to ISO 3166-1, for example `'EN-US'`, or `'PT-BR'`. A target
language without a variant translates into its default variant, for example
`'EN'` into `'EN-US'` and `'PT'` into `'PT-PT'`; specify the variant to choose
explicitly. The full list of supported languages is in the
[API documentation][api-docs-lang-list]. Language codes are plain strings; the
language code constants of `deepl.Language` (for example `Language.GERMAN`) are
deprecated and will be removed in the next major version.

There are additional optional arguments to control translation, see
[Text translation options](#text-translation-options) below.

`translate_text()` returns a `TextResult`, or a list of `TextResult`s
corresponding to your input text(s). `TextResult` has the following properties:
- `text` is the translated text,
- `detected_source_lang` is the detected source language code,
- `billed_characters` is the number of characters billed for the translation,
  or `None` if the response does not contain it.
- `model_type_used` indicates the translation model used, but is `None` unless
  the `model_type` option is specified. 
- `tag_handling_version` is the version of the tag handling algorithm used, for
  example `'v2'`, but is `None` unless the `tag_handling` option is specified.

```python
# Translate text into a target language, in this case, French:
result = deepl_client.translate_text("Hello, world!", target_lang="FR")
print(result.text)  # "Bonjour, le monde !"

# Translate multiple texts into British English
result = deepl_client.translate_text(
    ["お元気ですか？", "¿Cómo estás?"],
    target_lang="EN-GB",
)
print(result[0].text)  # "How are you?"
print(result[0].detected_source_lang)  # "JA" the language code for Japanese
print(result[0].billed_characters)  # 7 - the number of characters in the source text "お元気ですか？"
print(result[1].text)  # "How are you?"
print(result[1].detected_source_lang)  # "ES" the language code for Spanish
print(result[1].billed_characters)  # 12 - the number of characters in the source text "¿Cómo estás?"

# Translate into German with less and more Formality:
print(
    deepl_client.translate_text(
        "How are you?", target_lang="DE", formality="less"
    )
)  # 'Wie geht es dir?'
print(
    deepl_client.translate_text(
        "How are you?", target_lang="DE", formality="more"
    )
)  # 'Wie geht es Ihnen?'
```

#### Text translation options

In addition to the input text(s) argument, the available `translate_text()`
arguments are:

- `source_lang`: Specifies the source language code, but may be omitted to
  auto-detect the source language.
- `target_lang`: Required. Specifies the target language code.
- `split_sentences`: specify how input text should be split into sentences,
  default: `'1'`.
    - `'1'` (`SplitSentences.ALL`): input text will be split into sentences
      using both newlines and punctuation. `SplitSentences.DEFAULT` is a
      deprecated alias of `SplitSentences.ALL`.
    - `'off'` (`SplitSentences.OFF`): input text will not be split into
      sentences. Use this for applications where each input text contains only
      one sentence.
    - `'nonewlines'` (`SplitSentences.NO_NEWLINES`): input text will be split
      into sentences using punctuation but not newlines.
- `preserve_formatting`: controls automatic-formatting-correction. Set to `True`
  to prevent automatic-correction of formatting, default: `False`.
- `formality`: controls whether translations should lean toward informal or
  formal language. This option is only available for some target languages, see
  [Listing available languages](#listing-available-languages).
    - `'less'` (`Formality.LESS`): use informal language.
    - `'more'` (`Formality.MORE`): use formal, more polite language.
  A string is sent unchanged, so pass the API's lower-case values.
- `glossary`: specifies a glossary to use with translation, either as a string
  containing the glossary ID, or a `GlossaryInfo` as returned by
  `get_glossary()`.
- `glossary_ids`: specifies a list of up to 5 glossaries to use with
  translation, applied in order. Each entry may be a string containing the
  glossary ID or a `GlossaryInfo` object. Cannot be combined with the
  `glossary` parameter. On the command line, use the
  repeatable `--glossary-ids` argument (available on both the `text` and
  `document` commands), for example:
  `--from=EN --to=DE --glossary-ids=ID1 --glossary-ids=ID2`.
- `context`: specifies additional context to influence translations, that is not
  translated itself. Characters in the `context` parameter are not counted toward billing.
  See the [API documentation][api-docs-context-param] for more information and
  example usage.
- `model_type`: specifies the type of translation model to use, options are:
  - `'quality_optimized'` (`ModelType.QUALITY_OPTIMIZED`): use a translation
    model that maximizes translation quality, at the cost of response time. 
    This option may be unavailable for some language pairs.
  - `'prefer_quality_optimized'` (`ModelType.PREFER_QUALITY_OPTIMIZED`): use 
    the highest-quality translation model for the given language pair.
  - `'latency_optimized'` (`ModelType.LATENCY_OPTIMIZED`): use a translation
    model that minimizes response time, at the cost of translation quality.
- `tag_handling`: type of tags to parse before translation, options are `'html'`
  (`TagHandlingMode.HTML`) and `'xml'` (`TagHandlingMode.XML`).
- `tag_handling_version`: specifies which version of the tag handling algorithm to
  use, options are `'v1'` (`TagHandlingVersion.V1`) and `'v2'`
  (`TagHandlingVersion.V2`).
- `style_rule`: specifies a style rule to use with translation, either as a string
  containing the ID of the style rule, or a `StyleRuleInfo` object.
- `style_profile`: specifies a style profile to use with translation, either as
  a string containing the ID of the style profile, or a `StyleProfile` object.
  The profile's glossaries, style rule lists and translation memories are
  applied per text once the source language is known; a component that does
  not fit the language pair is left out. Cannot be combined with `glossary`,
  `glossary_ids`, `style_rule`, `translation_memory`,
  `translation_memory_threshold` or `custom_instructions`; the API rejects such
  requests.
- `translation_memory`: specifies a translation memory to use with translation,
  either as a string containing the ID of the translation memory, or a
  `TranslationMemoryInfo` object.
- `translation_memory_threshold`: the minimum matching percentage for fuzzy
  matches from the translation memory (0-100). We recommend a minimum threshold
  of 75%.
- `custom_instructions`: an array of instructions to customize the text 
  translation behavior. Up to 10 custom instructions can be specified, each with 
  a maximum of 300 characters.
  Important: The target language must be `de`, `en`, `es`, `fr`, `it`, `ja`, 
  `ko`, `zh` or any variants of these languages.
  Note: Any request with the `custom_instructions` parameter enabled will use
  the `quality_optimized` model type as the default. Requests combining
  `custom_instructions` and `model_type: latency_optimized` will be rejected.
- `extra_body_parameters`: Dictionary of extra parameters to pass in the body of
  the HTTP request. Mostly used by DeepL employees to test functionality, or for
  beta programs.

The following options are only used if `tag_handling` is `'xml'`:

- `outline_detection`: specify `False` to disable automatic tag detection,
  default is `True`.
- `splitting_tags`: list of XML tags that should be used to split text into
  sentences. Tags may be specified as an array of strings (`['tag1', 'tag2']`),
  or a comma-separated list of strings (`'tag1,tag2'`). The default is an empty
  list.
- `non_splitting_tags`: list of XML tags that should not be used to split text
  into sentences. Format and default are the same as for `splitting_tags`.
- `ignore_tags`: list of XML tags that containing content that should not be
  translated. Format and default are the same as for `splitting_tags`.

For a detailed explanation of the XML handling options, see the
[API documentation][api-docs-xml-handling].

### Improving text (Write API)

You can use the Write API to improve or rephrase text. This is implemented in
the `rephrase_text()` method. The first argument is a string containing the text
you want to translate, or a list of strings if you want to translate multiple texts.

`target_lang` optionally specifies the target language, e.g. when you want to change
the variant of a text (for example, you can send an english text to the write API and
use `target_lang` to turn it into British or American English). Please note that the
Write API itself does NOT translate. If you wish to translate and improve a text, you
will need to make multiple calls in a chain.

Language codes are the same as for translating text.

Example call:

```python
result = deepl_client.rephrase_text("A rainbouw has seven colours.", target_lang="EN-US")
print(result.text)
```

Additionally, you can optionally specify a style OR a tone (not both at once) that the
improvement should be in. The following styles are supported (`default` will be used if
nothing is selected):

- `academic`
- `business`
- `casual`
- `default`
- `simple`

The following tones are supported (`default` will be used if nothing is selected):

- `confident`
- `default`
- `diplomatic`
- `enthusiastic`
- `friendly`

You can also prefix any non-default style or tone with `prefer_` (`prefer_academic`, etc.),
in which case the style/tone will only be applied if the language supports it. If you do not
use `prefer_`, requests with `target_lang`s or detected languages that do not support
styles and tones will fail. The current list of supported languages can be found in our
[API documentation][api-docs]. We plan to also expose this information via an API endpoint
in the future.

Pass the style as `writing_style` and the tone as `tone`, either as a string or
as one of the predefined constants `WritingStyle` and `WritingTone`:

```python
result = deepl_client.rephrase_text(
    "A rainbouw has seven colours.", target_lang="EN-US", writing_style=WritingStyle.BUSINESS
)
print(result.text)
```

The `style` keyword is a deprecated alias of `writing_style`; it still works but
emits a `DeprecationWarning`.

To only fix spelling and grammar without rewriting the text for style or tone,
use `correct_text()`, which takes the text and the optional `target_lang`:

```python
result = deepl_client.correct_text("A rainbouw has seven colours.")
print(result.text)
```

Both `rephrase_text()` and `correct_text()` accept `extra_body_parameters`: a
dictionary of extra parameters to pass in the body of the HTTP request, as for
`translate_text()`. Its entries replace parameters of the same name set by the
library.

### Translating documents

To translate documents, you may call either `translate_document()` using file IO
objects, or `translate_document_from_filepath()` using file paths. For both
functions, the first and second arguments correspond to the input and output
files respectively.

Just as for the `translate_text()` function, the `source_lang` and
`target_lang` arguments specify the source and target language codes. They
may be passed as keywords or positionally after the input and output files,
for example `translate_document_from_filepath(input_path, output_path, "EN",
"DE")`.

There are additional optional arguments to control translation, see
[Document translation options](#document-translation-options) below.

```python
# Translate a formal document from English to German
input_path = "/path/to/Instruction Manual.docx"
output_path = "/path/to/Bedienungsanleitung.docx"
try:
    # Using translate_document_from_filepath() with file paths 
    deepl_client.translate_document_from_filepath(
        input_path,
        output_path,
        target_lang="DE",
        formality="more"
    )

    # Alternatively you can use translate_document() with file IO objects
    with open(input_path, "rb") as in_file, open(output_path, "wb") as out_file:
        deepl_client.translate_document(
            in_file,
            out_file,
            target_lang="DE",
            formality="more"
        )

except deepl.DocumentTranslationException as error:
    # If an error occurs during document translation, a
    # DocumentTranslationException is raised. If the document was already
    # uploaded, the document_handle property contains the document handle that
    # may be used to later retrieve the document from the server, or contact
    # DeepL support. If the upload itself failed, document_handle is None.
    if error.document_handle is not None:
        doc_id = error.document_handle.document_id
        doc_key = error.document_handle.document_key
        print(f"Error after uploading {error}, id: {doc_id} key: {doc_key}")
    else:
        print(f"Error during upload: {error}")
```

`DocumentTranslationException` copies `http_status_code` and `should_retry`
from the underlying `DeepLException`, if there is one.
`translate_document_from_filepath()` raises `ValueError` before any request if
the input file does not exist; if the input or output file cannot be opened,
it raises `DocumentTranslationException` with `document_handle` set to `None`.

`translate_document()` and `translate_document_from_filepath()` are convenience
functions that wrap multiple API calls: uploading, polling status until the
translation is complete, and downloading. If your application needs to execute
these steps individually, you can instead use the following functions directly:

- `translate_document_upload()`,
- `translate_document_get_status()` (or
  `translate_document_wait_until_done()`), and
- `translate_document_download()`

`translate_document_get_status()` returns a `DocumentStatus` with the
`document_id`, `status`, `seconds_remaining`, `billed_characters` and
`error_message` of the document, and the `done` (translation succeeded) and
`ok` (translation has not failed) properties. A status value this library
version does not know is kept as a string in `status`.
`translate_document_wait_until_done()` polls the status until the translation
is done and returns the final `DocumentStatus`; if the translation fails it
raises a `DeepLException` with the API's error message.

`translate_document_download()` writes the translated document to the
file-like object given as `output_file`, in chunks of `chunk_size` bytes
(default 64 KiB). Calling it without `output_file` returns the streaming
`requests.Response` instead; this is deprecated, emits a `DeprecationWarning`,
and `output_file` will be required in the next major version. If the download
fails, the raised exception carries the API's error message.

#### Document translation options

In addition to the input file, output file, `source_lang` and `target_lang`
arguments, the available `translate_document()` and
`translate_document_from_filepath()` arguments are:

- `formality`: same as in [Text translation options](#text-translation-options).
- `glossary`: same as in [Text translation options](#text-translation-options).
- `glossary_ids`: same as in [Text translation options](#text-translation-options).
- `style_rule`: same as in [Text translation options](#text-translation-options).
- `style_profile`: same as in [Text translation options](#text-translation-options).
  A style profile that does not exist is not rejected at upload; the
  translation fails with a `DocumentTranslationException`.
- `translation_memory`: same as in [Text translation options](#text-translation-options).
- `translation_memory_threshold`: same as in [Text translation options](#text-translation-options).
- `output_format`: (`translate_document()` only)
  file extension of desired format of translated file, for example: `'pdf'`. If
  unspecified, by default the translated file will be in the same format as the
  input file. 
- `enable_watermark`: set to `True` to add a "Translated by DeepL" watermark to
  the translated document. Only supported for `docx` and `pdf` output; for
  other output formats the API ignores it. If unspecified, the parameter is not
  sent and no watermark is added.

### Glossaries

Glossaries allow you to customize your translations using user-defined terms.
Multiple glossaries can be stored with your account, each with a user-specified
name and a uniquely-assigned ID.

#### v2 versus v3 glossary APIs

The newest version of the glossary APIs are the `/v3` endpoints, allowing both
editing functionality plus support for multilingual glossaries. New methods and
objects have been created to support interacting with these new glossaries. 
Due to this  new functionality, users are recommended to utilize these 
multilingual glossary methods. However, to continue using the `v2` glossary API 
endpoints, please continue to use the existing endpoints in the `translator.py` 
(e.g. `create_glossary()`, `get_glossary()`, etc).

To migrate to use the new multilingual glossary methods from the current 
monolingual glossary methods, please refer to 
[this migration guide](upgrading_to_multilingual_glossaries.md).

The following sections describe how to interact with multilingual glossaries 
using the new functionality:

#### Creating a glossary

You can create a multi-lingual glossary with your desired terms and name using
`create_multilingual_glossary()`. Glossaries created via the /v3 endpoints can now 
support multiple source-target language pairs. Note: Glossaries are only 
supported for some language pairs, see
[Listing available glossary languages](#listing-available-glossary-languages)
for more information. The entries should be specified as a dictionary, in
`MultilingualGlossaryDictionaryEntries` objects passed as `dictionaries`.
`MultilingualGlossaryDictionaryEntries`, `MultilingualGlossaryInfo` and
`MultilingualGlossaryDictionaryInfo` can be imported from the `deepl` package.

If successful, the glossary is created and stored with your DeepL account, and
a `MultilingualGlossaryInfo` object is returned including the ID, name, and glossary
dictionaries. The glossary dictionaries would be an array of 
`MultilingualGlossaryDictionaryInfo` objects, each containing its own languages and 
entry count.

```python
from deepl import MultilingualGlossaryDictionaryEntries

# Create a glossary with an English to German dictionary containing two terms:
entries = {"artist": "Maler", "prize": "Gewinn"}
dictionaries = [MultilingualGlossaryDictionaryEntries("EN", "DE", entries)]
my_glossary = deepl_client.create_multilingual_glossary(
    "My glossary",
    dictionaries
)
my_glossary_dict = my_glossary.dictionaries[0]
print(
    f"Created '{my_glossary.name}' ({my_glossary.glossary_id}) "
    f"with {len(my_glossary.dictionaries)} dictionary where "
    f"its language pair is {my_glossary_dict.source_lang}->"
    f"{my_glossary_dict.target_lang} containing "
    f"{my_glossary.entry_count} entries"
)
# Example: Created 'My glossary' (559192ed-8e23-...) with 1 dictionary where
# its language pair is EN->DE containing 2 entries
```

You can also upload a glossary downloaded from the DeepL website using
`create_multilingual_glossary_from_csv()`. Instead of supplying the entries as a 
dictionary within a MultilingualGlossaryDictionaryEntries object, you can specify 
the CSV data as `csv` either as a file-like object or string or bytes 
containing file content (`csv_data` is the deprecated name of this argument):

```python
# Open the CSV file assuming UTF-8 encoding. If your file contains a BOM,
# consider using encoding='utf-8-sig' instead.
with open('/path/to/glossary_file.csv', 'r',  encoding='utf-8') as csv_file:
    csv_data = csv_file.read()  # Read the file contents as a string
    my_csv_glossary = deepl_client.create_multilingual_glossary_from_csv(
        "CSV glossary",
        source_lang="EN",
        target_lang="DE",
        csv=csv_data,
    )
```

The [API documentation][api-docs-csv-format] explains the expected CSV format in
detail.

#### Getting, listing, and deleting stored glossaries

Functions to get, list, and delete stored glossaries are also provided:

- `get_multilingual_glossary()` takes a glossary ID or `MultilingualGlossaryInfo`
  object and returns a 
  `MultilingualGlossaryInfo` object for a stored glossary, or raises an 
  exception if no such glossary is found.
- `list_multilingual_glossaries()` returns a list of `MultilingualGlossaryInfo` objects 
  corresponding to all of your stored glossaries.
- `delete_multilingual_glossary()` takes a glossary ID or `MultilingualGlossaryInfo` 
  object and deletes the stored glossary from the server, or raises an 
  exception if no such glossary is found.
- `delete_multilingual_glossary_dictionary()` takes a glossary ID or `GlossaryInfo` object to 
  identify the glossary. Additionally takes in a source and target language or a 
  `MultilingualGlossaryDictionaryInfo` object and deletes the stored dictionary
   from the server, or raises an exception if no such glossary dictionary is found.

```python
# Retrieve a stored glossary using the ID
glossary_id = "559192ed-8e23-..."
my_glossary = deepl_client.get_multilingual_glossary(glossary_id)

# Delete a glossary dictionary from a stored glossary
deepl_client.delete_multilingual_glossary_dictionary(my_glossary, my_glossary.dictionaries[0])

# Find and delete glossaries named 'Old glossary'
glossaries = deepl_client.list_multilingual_glossaries()
for glossary in glossaries:
    if glossary.name == "Old glossary":
        deepl_client.delete_multilingual_glossary(glossary)
```

#### Listing entries in a stored glossary

The `MultilingualGlossaryInfo` object does not contain the glossary entries, but
instead only the number of entries in the `entry_count` property.

To list the entries of one dictionary within a stored glossary, use
`get_multilingual_glossary_dictionary_entries()` providing either the
`MultilingualGlossaryInfo` object or glossary ID, and the source and target
language. It returns a `MultilingualGlossaryDictionaryEntries` object whose
`entries` is a dictionary of source-target terms, and raises a
`GlossaryNotFoundException` if the glossary has no dictionary for that language
pair:

```python
dictionary = deepl_client.get_multilingual_glossary_dictionary_entries(
    my_glossary, "EN", "DE"
)
print(dictionary.entries)  # "{'artist': 'Maler', 'prize': 'Gewinn'}"
```

`get_multilingual_glossary_entries()` is deprecated: it returns a
`MultilingualGlossaryDictionaryEntriesResponse` wrapping a list of
dictionaries. Use `get_multilingual_glossary_dictionary_entries()` instead.

#### Editing a glossary

Functions to edit stored glossaries are also provided:

- `update_multilingual_glossary()` takes a glossary ID or `MultilingualGlossaryInfo`
  object, plus the optional keyword arguments `name` (the new name) and
  `dictionaries` (a list of `MultilingualGlossaryDictionaryEntries` to merge into
  the glossary, as `update_multilingual_glossary_dictionary()` does for one).
  Only the arguments that are set are sent.
- `update_multilingual_glossary_dictionary()` takes a glossary ID or `MultilingualGlossaryInfo`
  object, plus a `dictionary`: a `MultilingualGlossaryDictionaryEntries` with
  a source language, target language, and a dictionary of entries.
  It will then either update the list of entries for that dictionary (either 
  inserting new entires or replacing the target phrase for any existing 
  entries) or will insert a new glossary dictionary if that language pair is 
  not currently in the stored glossary.
- `replace_multilingual_glossary_dictionary()` takes a glossary ID or `MultilingualGlossaryInfo`
  object, plus a `dictionary`: a `MultilingualGlossaryDictionaryEntries` with
  a source language, target language, and a dictionary of entries.
  It will then either set the entries to the parameter value, completely 
  replacing any pre-existing entries for that language pair.
- `update_multilingual_glossary_name()` takes a glossary ID or `MultilingualGlossaryInfo`
  object, plus the new name of the glossary. 

The `*_from_csv()` variants take the entries as `csv` instead. The
`glossary_dicts` (of `create_multilingual_glossary()`), `glossary_dict` and
`csv_data` argument names are deprecated; use `dictionaries`, `dictionary` and
`csv`. `get_multilingual_glossary()` likewise takes `glossary`; its
`glossary_id` keyword is deprecated.

The functions that create, update or replace glossaries and dictionaries
(`create_multilingual_glossary()`, `create_multilingual_glossary_from_csv()`,
`update_multilingual_glossary()`, `update_multilingual_glossary_name()`,
`update_multilingual_glossary_dictionary()`,
`update_multilingual_glossary_dictionary_from_csv()`,
`replace_multilingual_glossary_dictionary()` and
`replace_multilingual_glossary_dictionary_from_csv()`) also accept
`extra_body_parameters`: a dictionary of additional fields for the JSON request
body. They are added last and replace fields with the same key.

```python
# Update glossary dictionary
entries = {"artist": "Maler", "hello": "guten tag"}
dictionaries = [MultilingualGlossaryDictionaryEntries("EN", "DE", entries)]
my_glossary = deepl_client.create_multilingual_glossary(
    "My glossary",
    dictionaries
)
new_entries = {"hello": "hallo", "prize": "Gewinn"}
glossary_dict = MultilingualGlossaryDictionaryEntries("EN", "DE", new_entries)
updated_glossary = deepl_client.update_multilingual_glossary_dictionary(
    my_glossary,
    glossary_dict
)

dictionary = deepl_client.get_multilingual_glossary_dictionary_entries(my_glossary, "EN", "DE")
print(dictionary.entries)  # "{'artist': 'Maler', 'hello': 'hallo', 'prize': 'Gewinn'}"

# Update a glossary dictionary from CSV
# Open the CSV file assuming UTF-8 encoding. If your file contains a BOM,
# consider using encoding='utf-8-sig' instead.
with open('/path/to/glossary_file.csv', 'r',  encoding='utf-8') as csv_file:
    csv_data = csv_file.read()  # Read the file contents as a string
    my_csv_glossary = deepl_client.update_multilingual_glossary_dictionary_from_csv(
        glossary="4c81ffb4-2e...",
        source_lang="EN",
        target_lang="DE",
        csv=csv_data,
    )

# Replace glossary dictionary
replacement_entries = {"goodbye": "Auf Wiedersehen"}
glossary_dict = MultilingualGlossaryDictionaryEntries("EN", "DE", replacement_entries)
updated_glossary = deepl_client.replace_multilingual_glossary_dictionary(
  my_glossary,
  glossary_dict)
dictionary = deepl_client.get_multilingual_glossary_dictionary_entries(my_glossary, "EN", "DE")
print(dictionary.entries)  # "{'goodbye': 'Auf Wiedersehen'}"

# Replace a glossary dictionary from CSV
# Open the CSV file assuming UTF-8 encoding. If your file contains a BOM,
# consider using encoding='utf-8-sig' instead.
with open('/path/to/glossary_file.csv', 'r',  encoding='utf-8') as csv_file:
    csv_data = csv_file.read()  # Read the file contents as a string
    my_csv_glossary = deepl_client.replace_multilingual_glossary_dictionary_from_csv(
        glossary="4c81ffb4-2e...",
        source_lang="EN",
        target_lang="DE",
        csv=csv_data,
    )

# Update the glossary name
updated_glossary = deepl_client.update_multilingual_glossary_name(
  my_glossary,
  "My new glossary name"
)
print(updated_glossary.name) # 'My new glossary name'

# Rename the glossary and merge entries in one request
updated_glossary = deepl_client.update_multilingual_glossary(
    my_glossary,
    name="My renamed glossary",
    dictionaries=[MultilingualGlossaryDictionaryEntries("EN", "DE", {"cat": "Katze"})],
)
```

#### Using a stored glossary

You can use a stored glossary for text translation by setting the `glossary`
argument to either the glossary ID or `GlossaryInfo`/`MultilingualGlossaryInfo` object.
The `source_lang` argument is optional: if you omit it, DeepL detects the
source language and uses the glossary dictionary for the detected language pair:

```python
text = "The artist was awarded a prize."
with_glossary = deepl_client.translate_text(
    text, source_lang="EN", target_lang="DE", glossary=my_glossary,
)
print(with_glossary)  # "Der Maler wurde mit einem Gewinn ausgezeichnet."

# For comparison, the result without a glossary:
without_glossary = deepl_client.translate_text(text, target_lang="DE")
print(without_glossary)  # "Der Künstler wurde mit einem Preis ausgezeichnet."
```

Using a stored glossary for document translation is the same, except that the
`source_lang` argument is required:

```python
deepl_client.translate_document(
    in_file, out_file, source_lang="EN", target_lang="DE", glossary=my_glossary,
)
```

The `translate_document()`, `translate_document_from_filepath()` and
`translate_document_upload()` functions all support the `glossary` argument.

### Spoken terms

A spoken-terms collection holds terms, such as product names or technical
words, that improve speech transcription. Each collection has one term list
per language; a term list is a list of strings. Before sending, the library
strips leading and trailing whitespace from each term and sends the stripped
term, then checks it like a glossary term (`validate_glossary_term()`): an
empty term or one with a control character, such as a newline, raises
`ValueError`. The API validates the rest (at most 300 characters per list, no
duplicates). Methods that take a collection accept either its ID or a
`SpokenTerms` object. `create_spoken_terms()`, `update_spoken_terms()` and
`replace_spoken_terms_list()` accept the keyword argument
`extra_body_parameters`: a dictionary of extra fields to send in the JSON
request body, replacing fields the library sets with the same key.

```python
# Create a collection with an English term list
spoken_terms = deepl_client.create_spoken_terms(
    "My spoken terms",
    [deepl.SpokenTermsEntries("en", ["DeepL", "webhook"])],
)
print(spoken_terms.spoken_terms_id, spoken_terms.name)
for term_list in spoken_terms.term_lists:
    print(term_list.lang, term_list.entry_count)  # en 2

# Retrieve a collection, and list all collections
spoken_terms = deepl_client.get_spoken_terms(spoken_terms.spoken_terms_id)
for collection in deepl_client.list_spoken_terms():
    print(collection.name)

# Rename the collection and merge terms into the English term list
spoken_terms = deepl_client.update_spoken_terms(
    spoken_terms,
    name="My renamed spoken terms",
    term_lists=[deepl.SpokenTermsEntries("en", ["authentication"])],
)

# Read the terms of one language
entries = deepl_client.get_spoken_terms_entries(spoken_terms, "en")
print(entries.entries)  # ['DeepL', 'authentication', 'webhook']

# Replace the term list of one language, or add it if it is new
term_list = deepl_client.replace_spoken_terms_list(
    spoken_terms, deepl.SpokenTermsEntries("de", ["Schnittstelle"])
)
print(term_list.lang, term_list.entry_count)  # de 1

# Delete the term list of one language, then the whole collection
deepl_client.delete_spoken_terms_list(spoken_terms, "de")
deepl_client.delete_spoken_terms(spoken_terms)
```

### Checking account usage

To check account usage, use the `get_usage()` function.

The returned `Usage` object contains three usage subtypes: `character`,
`document` and `team_document`. Depending on your account type, some usage
subtypes may be invalid; this can be checked using the `valid` property. For API
accounts:

- `usage.character.valid` is `True`,
- `usage.document.valid` and `usage.team_document.valid` are `False`.

Each usage subtype (if valid) has `count` and `limit` properties giving the
amount used and maximum amount respectively, and the `limit_reached` property
that checks if the usage has reached the limit. The top level `Usage` object has
the `any_limit_reached` property to check the `character`, `document` and
`team_document` subtypes. It does not consider the API Pro subtypes described
below; check `limit_reached` on those directly.

```python
usage = deepl_client.get_usage()
if usage.any_limit_reached:
    print('Translation limit reached.')
if usage.character.valid:
    print(
        f"Character usage: {usage.character.count} of {usage.character.limit}")
if usage.document.valid:
    print(f"Document usage: {usage.document.count} of {usage.document.limit}")
```

API Pro accounts also receive the following; for other accounts, and whenever
the response does not contain them, these properties are `None`:

- `api_key_character`: character usage of the API key making the request, as
  opposed to `character`, which covers the whole account,
- `speech_to_text_minutes` and `speech_to_speech_minutes`: speech usage in
  minutes,
- `start_time` and `end_time`: the current billing period as `datetime`
  objects,
- `products`: a list of `Usage.Product` objects, one per product, with
  `product_type` (for example `"translate"`, `"write"`, `"speechToText"`),
  `billing_unit` (for example `"characters"` or `"minutes"`),
  `api_key_unit_count` and `account_unit_count`.

```python
usage = deepl_client.get_usage()
if usage.start_time and usage.end_time:
    print(f"Billing period: {usage.start_time} to {usage.end_time}")
print(f"Account characters: {usage.character.count} of {usage.character.limit}")
if usage.api_key_character and usage.api_key_character.valid:
    print(
        f"API key characters: {usage.api_key_character.count} of "
        f"{usage.api_key_character.limit}"
    )
for product in usage.products or []:
    print(
        f"{product.product_type}: {product.api_key_unit_count} (API key) / "
        f"{product.account_unit_count} (account) {product.billing_unit}"
    )
```

### Listing available languages

You can request the list of languages supported by DeepL for text and documents
using the `get_source_languages()` and `get_target_languages()` functions. They
both return a list of `Language` objects.

The `name` property gives the name of the language in English, and the `code`
property gives the language code. The `supports_formality` property only appears
for target languages, and indicates whether the target language supports the
optional `formality` parameter.

```python
print("Source languages:")
for language in deepl_client.get_source_languages():
    print(f"{language.name} ({language.code})")  # Example: "German (DE)"

print("Target languages:")
for language in deepl_client.get_target_languages():
    if language.supports_formality:
        print(f"{language.name} ({language.code}) supports formality")
        # Example: "Italian (IT) supports formality"
    else:
        print(f"{language.name} ({language.code})")
        # Example: "Lithuanian (LT)"
```

#### Listing languages per resource

`get_languages_for_resource()` uses the `/v3/languages` endpoint and returns
the languages supported by one resource (`LanguageResourceName.TRANSLATE_TEXT`,
`LanguageResourceName.WRITE`, etc.) as a list of `LanguageSupport` objects. Each
has `code`, `name`, `status`, `usable_as_source`, `usable_as_target` and a
`features` map from feature name to its support status. By default only stable
languages and features are returned; pass `include=[LanguageInclude.BETA]` to
also get beta ones.

```python
from deepl.api_data import LanguageResourceName

for language in deepl_client.get_languages_for_resource(
    LanguageResourceName.TRANSLATE_TEXT
):
    if language.usable_as_target and language.supports("formality"):
        print(f"{language.name} ({language.code}) supports formality")
        # Example: "German (de) supports formality"
```

#### Listing resources and their features

`get_language_resources()` uses the `/v3/languages/resources` endpoint and
returns the resources the API offers (translate_text, glossary, write, etc.) as
a list of `LanguageResource` objects. Each has `name` (the resource name),
`features` (a map from feature name to `ResourceFeature`) and
`supports(feature)`. A `ResourceFeature` has `name`, `needs_source_support` and
`needs_target_support`: `True` means the source (or target) language must
support the feature for it to be available; they are `False` when the API
omits them.

```python
for resource in deepl_client.get_language_resources():
    for feature in resource.features.values():
        if feature.needs_target_support:
            print(f"{resource.name}: {feature.name} needs target support")
            # Example: "translate_text: formality needs target support"
```

#### Listing available glossary languages

Glossaries are supported for a subset of language pairs. To retrieve those
languages use the `get_glossary_languages()` function, which returns an array
of `GlossaryLanguagePair` objects. Each has `source_lang` and `target_lang`
properties indicating that that pair of language codes is supported.

```python
glossary_languages = deepl_client.get_glossary_languages()
for language_pair in glossary_languages:
    print(f"{language_pair.source_lang} to {language_pair.target_lang}")
    # Example: "EN to DE", "DE to EN", etc.
```

You can also find the list of supported glossary language pairs in the
[API documentation][api-docs-glossary-lang-list].

Note that glossaries work for all target regional-variants: a glossary for the
target language English (`"EN"`) supports translations to both American English
(`"EN-US"`) and British English (`"EN-GB"`).


### Style Rules

Style rules allow you to customize your translations using a managed, shared list
of rules for style, formatting, and more. Multiple style rules can be stored with
your account, each with a user-specified name and a uniquely-assigned ID.

#### Creating a style rule

Use `create_style_rule()` to create a new style rule with a name and language
code. You can optionally provide `configured_rules` and `custom_instructions`.

```python
style_rule = deepl_client.create_style_rule(
    name="My Style Rule",
    language="en",
)
print(f"Created: {style_rule.name} ({style_rule.style_id})")
```

#### Retrieving and listing style rules

Use `get_style_rule()` to retrieve a single style rule by ID, or
`get_all_style_rules()` to list all style rules.

`get_all_style_rules()` returns a list of `StyleRuleInfo` objects
corresponding to all of your stored style rules. The method accepts optional
parameters: `page` (page number for pagination, 0-indexed), `page_size` (number
of items per page), and `detailed`. When `True`, the response includes
`configured_rules` and `custom_instructions` for each style rule. When `False`
(default), these fields are omitted for faster responses.

```python
# Get a single style rule by ID
style_rule = deepl_client.get_style_rule("YOUR_STYLE_ID")
print(f"{style_rule.name} ({style_rule.language})")

# List all style rules
style_rules = deepl_client.get_all_style_rules()
for rule in style_rules:
    print(f"{rule.name} ({rule.style_id})")

# List with detailed configuration
style_rules = deepl_client.get_all_style_rules(detailed=True)
for rule in style_rules:
    if rule.configured_rules:
        print(f"  Number formatting: {rule.configured_rules.numbers}")
```

#### Updating a style rule

Use `update_style_rule_name()` to rename a style rule, and
`update_style_rule_configured_rules()` to update its configured rules.

```python
# Update the name
updated = deepl_client.update_style_rule_name("YOUR_STYLE_ID", "New Name")

# Update configured rules
updated = deepl_client.update_style_rule_configured_rules(
    "YOUR_STYLE_ID",
    {"style_and_tone": {"formality": "formal"}},
)
```

#### Managing custom instructions

Custom instructions allow you to add free-text prompts to a style rule. Use
`create_style_rule_custom_instruction()`, `get_style_rule_custom_instruction()`,
`update_style_rule_custom_instruction()`, and
`delete_style_rule_custom_instruction()` to manage them. The `style_rule`
argument of every style rule function takes a style rule ID or a
`StyleRuleInfo` object, and `instruction_id` takes a custom instruction ID or a
`CustomInstruction` object.

```python
# Create a custom instruction
instruction = deepl_client.create_style_rule_custom_instruction(
    "YOUR_STYLE_ID",
    label="Formal tone",
    prompt="Always use formal language",
)
print(f"Created instruction: {instruction.id}")

# Get a custom instruction
instruction = deepl_client.get_style_rule_custom_instruction(
    "YOUR_STYLE_ID", instruction.id
)

# Update a custom instruction
updated = deepl_client.update_style_rule_custom_instruction(
    "YOUR_STYLE_ID",
    instruction.id,
    label="Updated label",
    prompt="Use very formal language",
)

# Delete a custom instruction (by ID or CustomInstruction object)
deepl_client.delete_style_rule_custom_instruction("YOUR_STYLE_ID", instruction)
```

`create_style_rule()`, `update_style_rule_name()`,
`update_style_rule_configured_rules()`, `create_style_rule_custom_instruction()`
and `update_style_rule_custom_instruction()` also accept
`extra_body_parameters`: a dictionary of extra parameters to pass in the JSON
request body, which replace request fields of the same name. See the
`extra_body_parameters` [text translation option](#text-translation-options).

```python
deepl_client.update_style_rule_name(
    "YOUR_STYLE_ID", "New Name", extra_body_parameters={"beta_param": "value"}
)
```

#### Deleting a style rule

Use `delete_style_rule()` to delete a style rule by ID.

```python
deepl_client.delete_style_rule("YOUR_STYLE_ID")
```

#### Using a style rule in translations

Style rules can also be used with the command line interface for text
translation:

```bash
python3 -m deepl --auth-key=YOUR_AUTH_KEY text --to=DE --style-id=YOUR_STYLE_ID "Text to translate"
```

The `document` command also accepts `--style-id` for document translation:

```bash
python3 -m deepl --auth-key=YOUR_AUTH_KEY document --to=DE --style-id=YOUR_STYLE_ID /path/to/document.docx /path/to/output_dir
``` 

### Style profiles

A style profile bundles a name, an optional description and industry, and links
to glossaries, style rule lists and translation memories. Style profiles are
managed with `DeepLClient` and returned as `StyleProfile` objects.

#### Creating a style profile

Use `create_style_profile()`. Only the name is required. You can optionally
pass `description`, `industry`, `glossary_ids` (highest priority first),
`style_rule_ids`, `translation_memory_ids` and
`glossary_priority_order_enabled`. The component lists take IDs or the
objects themselves (`GlossaryInfo`, `MultilingualGlossaryInfo`,
`StyleRuleInfo`, `TranslationMemoryInfo`). If any of the component IDs cannot
be used, the request fails and no style profile is created.
`extra_body_parameters` is a dictionary of extra parameters for the JSON
request body; its keys replace parameters of the same name set by the client.

```python
# Without components
profile = deepl_client.create_style_profile("Legal, German")

# With components
profile = deepl_client.create_style_profile(
    "Legal, German",
    description="Contract wording for the German market.",
    industry="Legal",
    glossary_ids=["YOUR_GLOSSARY_ID"],
    style_rule_ids=[style_rule],  # a StyleRuleInfo object
    translation_memory_ids=["YOUR_TRANSLATION_MEMORY_ID"],
    glossary_priority_order_enabled=True,
)
print(f"Created: {profile.name} ({profile.style_profile_id})")
```

#### Retrieving and listing style profiles

Use `get_style_profile()` to retrieve a style profile by ID or `StyleProfile`
object, and `list_style_profiles()` to list them one page at a time. `page` is
0-indexed (default 0); `page_size` defaults to 10, and values above 100 are
reduced to 100.

```python
profile = deepl_client.get_style_profile("YOUR_STYLE_PROFILE_ID")
print(profile.style_rule_ids, profile.creation_time)

page = 0
while True:
    profiles = deepl_client.list_style_profiles(page=page, page_size=100)
    if not profiles:
        break
    for profile in profiles:
        print(f"{profile.name} ({profile.style_profile_id})")
    page += 1
```

#### Updating a style profile

Use `update_style_profile()` with the same options as `create_style_profile()`
(including `extra_body_parameters`) plus `name`. Options you leave out (`None`) are not changed. An empty string
clears `description` or `industry`. A component list replaces the linked list
in full, so an empty list unlinks all components of that kind.

```python
updated = deepl_client.update_style_profile(
    "YOUR_STYLE_PROFILE_ID",
    name="Legal, German (v2)",
    industry="Legal",
    description="",  # clears the description
    style_rule_ids=[],  # unlinks all style rule lists
)
```

#### Translating with a style profile

Pass a style profile, or its ID, as `style_profile` to `translate_text()` or to
the document translation functions to apply its glossaries, style rule lists
and translation memories through one option. On the command line, use
`--style-profile-id`.

```python
result = deepl_client.translate_text(
    "The artist is here.", target_lang="DE", style_profile=profile
)
deepl_client.translate_document_from_filepath(
    "/path/to/document.txt",
    "/path/to/output.txt",
    target_lang="DE",
    style_profile="YOUR_STYLE_PROFILE_ID",
)
```

#### Deleting a style profile

Use `delete_style_profile()` to delete a style profile by ID or `StyleProfile`
object. Getting, updating or deleting a style profile that does not exist
raises a `DeepLException` with `http_status_code` 404.

```python
deepl_client.delete_style_profile("YOUR_STYLE_PROFILE_ID")
```

### Translation Memories

Translation memories allow you to store and reuse previously created translations.
They can be used in text translation requests to improve consistency by matching
against stored segments. Multiple translation memories can be stored with your
account, each with a source language and one or more target languages.

#### Listing translation memories

`list_translation_memories()` returns a list of `TranslationMemoryInfo` objects
for your stored translation memories. The number of translation memories
returned is controlled by `page_size` (max 25). The method accepts
optional parameters: `page` (page number for pagination, 0-indexed)
and `page_size` (number of items per page).

```python
# List translation memories
translation_memories = deepl_client.list_translation_memories()
for tm in translation_memories:
    print(f"{tm.name} ({tm.translation_memory_id})")
    print(f"  Source: {tm.source_language}, Targets: {tm.target_languages}")
    print(f"  Segments: {tm.segment_count}")
```

#### Retrieving a translation memory

Use `get_translation_memory()` to retrieve a single translation memory by ID.
It accepts either a translation memory ID string or a `TranslationMemoryInfo`
object.

```python
tm = deepl_client.get_translation_memory("YOUR_TM_ID")
print(f"{tm.name}: {tm.segment_count} segments, updated {tm.updated_time}")
```

#### Listing the segments of a translation memory

`list_translation_memory_segments()` returns one page of segments as a
`TranslationMemorySegments` object. Pagination is cursor-based: omit
`page_cursor` on the first call, then pass the previous response's
`next_page_cursor` until it is `None`. Optionally filter with `filter_text`
(at least 2 characters, matched against both source and target text) and
`filter_case_sensitive`. Note that `segment_count` is the translation-memory
total and is not reduced by the filter.

```python
page_cursor = None
while True:
    page = deepl_client.list_translation_memory_segments(
        "YOUR_TM_ID", page_size=50, page_cursor=page_cursor
    )
    for segment in page.segments:
        print(segment.source_text)
        for target in segment.targets:
            print(f"  {target.target_language}: {target.target_text}")
    page_cursor = page.next_page_cursor
    if not page_cursor:
        break
```

#### Importing a translation memory

`import_translation_memory_from_filepath()` imports a TMX file as a new
translation memory: it creates the import job, uploads the file, and waits for
processing to finish. The returned `TranslationMemoryJob` carries the ID of the
new translation memory.

```python
job = deepl_client.import_translation_memory_from_filepath(
    "/path/to/legal.tmx", display_name="Legal TM", timeout_s=300
)
print(f"Created translation memory {job.result.translation_memory_id}")
print(f"Skipped segments: {job.result.skipped_segment_count}")
```

`import_translation_memory_from_filepath()` accepts these keyword arguments:

- `display_name`: name of the new translation memory, defaults to the file
  name.
- `timeout_s`: maximum time in seconds to wait for processing to finish.
- `content_type`: MIME type of the file, declared when creating the import job
  and sent with the upload. Defaults to `application/xml`.
- `extra_body_parameters`: dictionary of additional key/value pairs to include
  in the JSON body of the request that creates the import job, replacing keys
  of the same name that the library sets.

Importing takes a while: the API detects the uploaded file asynchronously, so
the job keeps reporting `awaiting_input` for roughly half a minute after the
upload before completing. Pass `timeout_s` to bound how long to wait.

The three steps are also available separately, for example to upload the file
yourself or to poll for progress. `create_translation_memory_import()` returns
an upload URL that the file must be uploaded to before processing starts, then
`get_translation_memory_job()` reports the status.
`create_translation_memory_import()` takes the file name and size, and the
optional keyword arguments `content_type`, `display_name` and
`extra_body_parameters`, with the same meaning as above.
`upload_translation_memory_file()` takes the import job (or its upload URL),
the file `content` as bytes or a binary file object, and an optional
`content_type` (default `application/xml`) that must match the one declared
when creating the job. The keyword `input_file` is a deprecated alias of
`content`: it emits a `DeprecationWarning` and will be removed in the next
major version.

```python
created = deepl_client.create_translation_memory_import(
    file_name="legal.tmx",
    content_length=os.path.getsize("/path/to/legal.tmx"),
    display_name="Legal TM",
)
with open("/path/to/legal.tmx", "rb") as input_file:
    deepl_client.upload_translation_memory_file(created, content=input_file)

# The job reports "awaiting_input" both before the upload and for a while
# afterwards, until the API detects it; this polls through that status.
job = deepl_client.wait_until_translation_memory_job_done(
    created.job_id, timeout_s=300
)
```

`TranslationMemoryJob.status` returns a `TranslationMemoryJobStatus` member
(`AWAITING_INPUT`, `PROCESSING`, `COMPLETED`, `FAILED` or `EXPIRED`), or the
plain string for a status the library does not know. Members are strings and
compare equal to the API value, so `job.status == "completed"` keeps working.

```python
if job.status == deepl.TranslationMemoryJobStatus.FAILED:
    print(f"Import failed: {job.result.error_message}")
```

#### Exporting a translation memory

`export_translation_memory_to_filepath()` exports a translation memory to a TMX
file: it creates the export job, waits for it to finish, and writes the result.

```python
job = deepl_client.export_translation_memory_to_filepath(
    "YOUR_TM_ID", "/path/to/exported.tmx"
)
```

As with import, the individual steps are available separately. Note that the
API may reuse a previously completed export of an unchanged translation memory,
indicated by `reused_existing`.

```python
created = deepl_client.create_translation_memory_export("YOUR_TM_ID")
job = deepl_client.wait_until_translation_memory_job_done(created.job_id)
with open("/path/to/exported.tmx", "wb") as output_file:
    deepl_client.download_translation_memory_export(
        job, output_file, chunk_size=8192
    )
```

`download_translation_memory_export()` writes in chunks of `chunk_size` bytes
(default 64 KiB). Calling it without `output_file` returns the streaming
`requests.Response` instead; this is deprecated, emits a `DeprecationWarning`,
and `output_file` will be required in the next major version.

#### Deleting a translation memory

Use `delete_translation_memory()` to delete a translation memory by ID.

```python
deepl_client.delete_translation_memory("YOUR_TM_ID")
```

#### Managing translation memories from the command line

The `translation-memory` command exposes the same operations:

```bash
python3 -m deepl --auth-key=YOUR_AUTH_KEY translation-memory list
python3 -m deepl --auth-key=YOUR_AUTH_KEY translation-memory get YOUR_TM_ID
python3 -m deepl --auth-key=YOUR_AUTH_KEY translation-memory segments YOUR_TM_ID --all
python3 -m deepl --auth-key=YOUR_AUTH_KEY translation-memory import /path/to/legal.tmx --name "Legal TM"
python3 -m deepl --auth-key=YOUR_AUTH_KEY translation-memory export YOUR_TM_ID /path/to/exported.tmx
python3 -m deepl --auth-key=YOUR_AUTH_KEY translation-memory job YOUR_JOB_ID
python3 -m deepl --auth-key=YOUR_AUTH_KEY translation-memory delete YOUR_TM_ID
```

#### Using a translation memory in translations

Pass the `translation_memory` parameter to `translate_text()` to use a
translation memory. You can pass either a string containing the translation
memory ID, or a `TranslationMemoryInfo` object. Use
`translation_memory_threshold` to control the minimum matching percentage for
fuzzy matches (0-100, recommended minimum of 75%).

```python
# Translate with a translation memory ID
result = deepl_client.translate_text(
    "Hello, world!",
    target_lang="DE",
    translation_memory="YOUR_TM_ID",
    translation_memory_threshold=80,
)

# Or use a TranslationMemoryInfo object
translation_memories = deepl_client.list_translation_memories()
result = deepl_client.translate_text(
    "Hello, world!",
    target_lang="DE",
    translation_memory=translation_memories[0],
)
```

Translation memories can also be used with the command line interface:

```bash
python3 -m deepl --auth-key=YOUR_AUTH_KEY text --to=DE --translation-memory-id=YOUR_TM_ID --translation-memory-threshold=75 "Text to translate"
```

The `document` command also accepts `--translation-memory-id` and
`--translation-memory-threshold` for document translation:

```bash
python3 -m deepl --auth-key=YOUR_AUTH_KEY document --to=DE --translation-memory-id=YOUR_TM_ID --translation-memory-threshold=75 /path/to/document.docx /path/to/output_dir
```

### Admin API

The Admin API lets you manage the developer keys of your organization and
retrieve usage analytics. It requires an admin API key, which you can create in
the "Admin API Keys" tab of your DeepL account. Admin keys cannot be used for
translation, and developer keys cannot access the Admin API.

Create a `DeepLAdminClient` with your admin key. It uses the
`https://api.deepl.com` server by default.

```python
import deepl

admin_client = deepl.DeepLAdminClient("YOUR_ADMIN_KEY")
```

#### Managing developer keys

```python
key = admin_client.create_developer_key(label="Staging Team Key")
print(f"Created {key.label} ({key.key_id})")

for k in admin_client.list_developer_keys():
    print(f"{k.label}: deactivated={k.is_deactivated}")

key = admin_client.rename_developer_key(key, "Production Team Key")

# Only the limits set in the DeveloperKeyUsageLimitsUpdate are changed; the
# others keep their current value. None removes a limit (unlimited usage) and 0
# blocks that usage.
key = admin_client.set_developer_key_usage_limits(
    key,
    deepl.DeveloperKeyUsageLimitsUpdate(
        characters=500000, speech_to_speech_milliseconds=None
    ),
)

# Deactivation is permanent.
admin_client.deactivate_developer_key(key)
```

`rename_developer_key()`, `set_developer_key_usage_limits()` and
`deactivate_developer_key()` accept either a key ID or a `DeveloperKey` object
and return the updated `DeveloperKey`.

`create_developer_key()`, `rename_developer_key()`,
`set_developer_key_usage_limits()` and `deactivate_developer_key()` also accept
`extra_body_parameters`, a dict of additional key/value pairs to include in the
JSON request body. They are added last and replace keys of the same name that
the client sets.

#### Retrieving usage analytics

`get_usage_analytics()` returns an `AdminUsageReport` for a date range. Dates
are UTC calendar days, and both the start and the end day are included. Pass
`datetime.date` objects or `YYYY-MM-DD` strings. For a `datetime.datetime`, the
UTC date of that moment is used, so `2026-10-20T00:00+02:00` is sent as
`2026-10-19`; a naive `datetime` is treated as UTC. The end date must be after
the start date, so a report covers at least two days, and at most 366 days
after it; otherwise the API raises a `DeepLException`. A value that is not a
date raises a `ValueError` before any request is sent. Use
`group_by` to break the usage down by key (`AdminUsageGroupBy.KEY`, see
`key_usages`) or by key and day (`AdminUsageGroupBy.KEY_AND_DAY`, see
`key_and_day_usages`). The lists are empty if the report is not grouped that
way. The `group_by` of an `AdminUsageReport` and the `aggregate_by` of a
`CustomTagUsageReport` are `AdminUsageGroupBy` and `CustomTagUsageAggregateBy`
members for known values; a value this library does not know is returned as
the string the API sent.

```python
report = admin_client.get_usage_analytics(
    "2026-06-01", "2026-07-01", group_by=deepl.AdminUsageGroupBy.KEY
)
print(f"Total characters: {report.total_usage.total_characters}")
for key_usage in report.key_usages:
    print(f"{key_usage.api_key_label}: {key_usage.usage.total_characters}")
```

`get_custom_tag_usage_analytics()` returns a `CustomTagUsageReport` with the
usage per custom tag. It accepts the same dates as `get_usage_analytics()`.
Use `aggregate_by` to choose between the whole period
(`CustomTagUsageAggregateBy.PERIOD`, the default) and per-day usage
(`CustomTagUsageAggregateBy.DAY`). The results are paginated: pass the
`next_page` value of a report as `page` to get the next page.

```python
page = None
while True:
    report = admin_client.get_custom_tag_usage_analytics(
        "2026-06-01", "2026-07-01", page=page
    )
    for tag_usage in report.usage:
        print(f"{tag_usage.custom_tag}: {tag_usage.breakdown.total_characters}")
    if report.next_page is None:
        break
    page = report.next_page
```

### Writing a Plugin

If you use this library in an application, please identify the application
with the name and version of the app. Use either the `app_info` option:

```python
deepl_client = deepl.DeepLClient(
    ..., app_info=deepl.AppInfo("sample_python_plugin", "1.0.2")
)
```

or, equivalently, `set_app_info()` after construction:

```python
deepl_client = deepl.DeepLClient(...).set_app_info("sample_python_plugin", "1.0.2")
```

This information is passed along when the library makes calls to the DeepL API.
Both name and version are required. Please note that a `User-Agent` header in the
`headers` option (or the deprecated `deepl.http_client.user_agent`) overrides this
setting; if you need to use one, please manually identify your application in it.

### Exceptions

All module functions may raise `deepl.DeepLException` or one of its subclasses.
If invalid arguments are provided, they may raise the standard exceptions
`ValueError` and `TypeError`.

| Exception | Raised for |
|---|---|
| `AuthorizationException` | HTTP 401 or 403: invalid or unauthorized key |
| `NotFoundException` | HTTP 404 on any endpoint |
| `QuotaExceededException` | HTTP 456: quota exceeded |
| `TooManyRequestsException` | HTTP 429 after all retries |
| `ConnectionException` | no HTTP response (connection failure, timeout) |
| `DeepLException` | any other error, including a non-2xx status not listed above (e.g. an HTTP 3xx that is not followed), with `http_status_code` set |

`should_retry` is `True` for HTTP 429 and 5xx errors. `GlossaryNotFoundException`,
raised for a 404 on glossary functions, is deprecated: it is a subclass of
`NotFoundException`, catch that instead. It will be removed in the next major
version.

### Configuration

#### Logging

Logging can be enabled to see the HTTP requests sent and responses received by
the library. Enable and control logging using Python's `logging` module, for
example:

```python
import logging

logging.basicConfig()
logging.getLogger('deepl').setLevel(logging.DEBUG)
```

#### Server URL configuration

You can override the URL of the DeepL API by specifying the `server_url`
argument when constructing a `deepl.DeepLClient`. This may be useful for
testing purposes. You **do not** need to specify the URL to distinguish API Free
and API Pro accounts, the library selects the correct URL automatically. A
`deepl.DeepLAdminClient` always uses `https://api.deepl.com` unless you give it
a `server_url`.

```python
server_url = "http://user:pass@localhost:3000"
deepl_client = deepl.DeepLClient(..., server_url=server_url)
```

A path in the server URL is kept: with `server_url="https://example.com/deepl"`
requests go to `https://example.com/deepl/v2/...`. The `server_url` property
returns the URL a client uses.

#### Custom HTTP headers

The `headers` option adds HTTP headers to every request to the DeepL API. A
`User-Agent` header replaces the one the library generates; an `Authorization`
header is ignored, the library always sends your key. `deepl.Translator` and
`deepl.DeepLAdminClient` accept the option too.

```python
deepl_client = deepl.DeepLClient(..., headers={"X-My-Header": "value"})
```

#### Proxy configuration

You can configure a proxy by specifying the `proxy` argument when constructing a
`deepl.DeepLClient`:

```python
proxy = "http://user:pass@10.10.1.10:3128"
deepl_client = deepl.DeepLClient(..., proxy=proxy)
```

The proxy argument is passed to the underlying `requests` session, see the
[documentation for requests][requests-proxy-docs]; a dictionary of schemes to
proxy URLs is also accepted.

#### Override SSL verification

You can control how `requests` performs SSL verification by specifying the 
`verify_ssl` option when constructing a `deepl.DeepLClient`, for example to
disable SSL certificate verification:

```python
deepl_client = deepl.DeepLClient(..., verify_ssl=False)
```

This option is passed to the underlying `requests` session as the `verify`
option, see the [documentation for requests][requests-verify-ssl-docs].

#### Configure automatic retries and timeouts

This SDK will automatically retry failed HTTP requests if the failures could
be transient: HTTP 429 and 5xx status codes, and network failures such as
refused or reset connections, DNS failures and timeouts. TLS and certificate
failures, and proxy failures (including a failure to connect to the proxy),
are not retried. By default a request is retried up to 5 times, and each
attempt has a timeout of at least 10 seconds. You can change both per client
with the `max_retries` and `timeout_s` options when
constructing a `deepl.DeepLClient`:

```python
deepl_client = deepl.DeepLClient(..., max_retries=3, timeout_s=30.0)
```

`max_retries` is the maximum number of retries after the first attempt (0
disables retries), and `timeout_s` is the minimum timeout in seconds for each
attempt. Both options are also accepted by `deepl.Translator` and
`deepl.DeepLAdminClient`.

`DeepLAdminClient.create_developer_key()` is only retried after an HTTP 429
status code or a DNS resolution failure, because a retry after any other
failure could create a second key.

The module-level settings `deepl.http_client.max_network_retries` and
`deepl.http_client.min_connection_timeout` are deprecated and will be removed
in a future major version. Assigning either setting emits a
`DeprecationWarning`. They still apply to clients created without the
corresponding option, and affect every client in the process:

```python
deepl.http_client.max_network_retries = 3  # deprecated, use max_retries
deepl.http_client.min_connection_timeout = 30.0  # deprecated, use timeout_s
```


#### Anonymous platform information

By default, we send some basic information about the platform the client library is running on with each request, see [here for an explanation](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent). This data is completely anonymous and only used to improve our product, not track any individual users. If you do not wish to send this data, you can opt-out when creating your `deepl.DeepLClient` object by setting the `send_platform_info` flag like so:

```python
deepl_client = deepl.DeepLClient(..., send_platform_info=False)
```

You can also replace the whole `User-Agent` with the `headers` option:

```python
deepl_client = deepl.DeepLClient(..., headers={"User-Agent": "my custom user agent"})
```

The module-level setting `deepl.http_client.user_agent`, which replaces the
library part of the `User-Agent` for every client in the process, is deprecated
in favour of the `headers` option and will be removed in the next major version.
Assigning it emits a `DeprecationWarning`.

## Command Line Interface

The library can be run on the command line supporting all API functions. Use the
`--help` option for usage information:

```shell
python3 -m deepl --help
```

The CLI requires your DeepL authentication key specified either as the
`DEEPL_AUTH_KEY` environment variable, through the `keyring` module, or
using the `--auth-key` option, for example:

```shell
python3 -m deepl --auth-key=YOUR_AUTH_KEY usage
```

Note that the `--auth-key` argument must appear *before* the command argument.
To use the [keyring](https://pypi.org/project/keyring/) module, set the 
*DEEPL_AUTH_KEY* field in the service *deepl* to your API key.
The recognized commands are:

| Command   | Description                                            |
| :-------- | :----------------------------------------------------- |
| text      | translate text(s)                                      |
| document  | translate document(s)                                  |
| usage     | print usage information for the current billing period |
| languages | print available languages                              |
| glossary  | create, list, and remove glossaries                    |

For example, to translate text:

```shell
python3 -m deepl --auth-key=YOUR_AUTH_KEY text --to=DE "Text to be translated."
```

Wrap text arguments in quotes to prevent the shell from splitting sentences into
words.

## Issues

If you experience problems using the library, or would like to request a new
feature, please open an [issue][issues].

## Development

We welcome Pull Requests, please read the
[contributing guidelines](CONTRIBUTING.md).

### Tests

The tests are split into two groups, selected by directory:

- `pytest tests/offline` runs the offline tests. They intercept all HTTP
  traffic with [responses][responses], so they need no network and no
  authentication key. They check the requests that the library sends for every
  option, and how it handles errors, retries and polling.
- `pytest tests/real_api` runs the real-API tests. They send one request per
  API endpoint to the DeepL API, using the authentication key defined by the
  `DEEPL_AUTH_KEY` environment variable and, for a non-default server, the
  server URL defined by `DEEPL_SERVER_URL`. The Admin API tests use the admin
  key defined by `DEEPL_ADMIN_KEY` instead.
  They create and delete glossaries, style rules, style profiles, translation
  memories and spoken-terms collections named `sdktest-python-...`, and create
  and deactivate developer keys with such labels.

Copy `.env.example` to `.env`, set your key and load it with
`set -a; . ./.env; set +a` before running the real-API tests. Be aware that the
real-API tests make DeepL API requests that contribute toward your API usage.

[api-docs]: https://www.deepl.com/docs-api?utm_source=github&utm_medium=github-python-readme

[api-docs-csv-format]: https://www.deepl.com/docs-api/managing-glossaries/supported-glossary-formats/?utm_source=github&utm_medium=github-python-readme

[api-docs-xml-handling]: https://www.deepl.com/docs-api/handling-xml/?utm_source=github&utm_medium=github-python-readme

[api-docs-context-param]: https://www.deepl.com/docs-api/translating-text/?utm_source=github&utm_medium=github-python-readme

[api-docs-lang-list]: https://www.deepl.com/docs-api/translating-text/?utm_source=github&utm_medium=github-python-readme

[api-docs-glossary-lang-list]: https://www.deepl.com/docs-api/managing-glossaries/?utm_source=github&utm_medium=github-python-readme

[bug-report-ubuntu-2204]: https://bugs.launchpad.net/ubuntu/+source/poetry/+bug/1958227

[create-account]: https://www.deepl.com/pro?utm_source=github&utm_medium=github-python-readme#developer

[issues]: https://www.github.com/DeepLcom/deepl-python/issues

[pypi-project]: https://pypi.org/project/deepl/

[pro-account]: https://www.deepl.com/pro-account/?utm_source=github&utm_medium=github-python-readme

[python-version-list]: https://devguide.python.org/versions/

[requests-proxy-docs]: https://docs.python-requests.org/en/latest/user/advanced/#proxies

[requests-verify-ssl-docs]: https://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification

[responses]: https://github.com/getsentry/responses
