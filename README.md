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

### Translating text

To translate text, call `translate_text()`. The first argument is a string
containing the text you want to translate, or a list of strings if you want to
translate multiple texts.

`source_lang` and `target_lang` specify the source and target language codes
respectively. The `source_lang` is optional, if it is unspecified the source
language will be auto-detected.

Language codes are **case-insensitive** strings according to ISO 639-1, for
example `'DE'`, `'FR'`, `'JA''`. Some target languages also include the regional
variant according to ISO 3166-1, for example `'EN-US'`, or `'PT-BR'`. The full
list of supported languages is in the
[API documentation][api-docs-lang-list].

There are additional optional arguments to control translation, see
[Text translation options](#text-translation-options) below.

`translate_text()` returns a `TextResult`, or a list of `TextResult`s
corresponding to your input text(s). `TextResult` has the following properties:
- `text` is the translated text,
- `detected_source_lang` is the detected source language code,
- `billed_characters` is the number of characters billed for the translation.
- `model_type_used` indicates the translation model used, but is `None` unless
  the `model_type` option is specified. 

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
  default: `'on'`.
    - `'on''` (`SplitSentences.ON`): input text will be split into sentences
      using both newlines and punctuation.
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
- `glossary`: specifies a glossary to use with translation, either as a string
  containing the glossary ID, or a `GlossaryInfo` as returned by
  `get_glossary()`.
- `glossary_ids`: specifies a list of up to 5 glossaries to use with
  translation, applied in order. Each entry may be a string containing the
  glossary ID or a `GlossaryInfo` object. Requires `source_lang` to be set and
  cannot be combined with the `glossary` parameter. On the command line, use the
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
  and `'xml'`.
- `tag_handling_version`: specifies which version of the tag handling algorithm to
  use, options are `'v1'` and `'v2'`.
- `style_rule`: specifies a style rule to use with translation, either as a string
  containing the ID of the style rule, or a `StyleRuleInfo` object.
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

You can use the predefined constants in the library to use a style:

```python
result = deepl_client.rephrase_text(
    "A rainbouw has seven colours.", target_lang="EN-US", style=WritingStyle.BUSINESS.value
)
print(result.text)
```

### Translating documents

To translate documents, you may call either `translate_document()` using file IO
objects, or `translate_document_from_filepath()` using file paths. For both
functions, the first and second arguments correspond to the input and output
files respectively.

Just as for the `translate_text()` function, the `source_lang` and
`target_lang` arguments specify the source and target language codes.

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
    # If an error occurs during document translation after the document was
    # already uploaded, a DocumentTranslationException is raised. The
    # document_handle property contains the document handle that may be used to
    # later retrieve the document from the server, or contact DeepL support.
    doc_id = error.document_handle.id
    doc_key = error.document_handle.key
    print(f"Error after uploading ${error}, id: ${doc_id} key: ${doc_key}")
except deepl.DeepLException as error:
    # Errors during upload raise a DeepLException
    print(error)
```

`translate_document()` and `translate_document_from_filepath()` are convenience
functions that wrap multiple API calls: uploading, polling status until the
translation is complete, and downloading. If your application needs to execute
these steps individually, you can instead use the following functions directly:

- `translate_document_upload()`,
- `translate_document_get_status()` (or
  `translate_document_wait_until_done()`), and
- `translate_document_download()`

#### Document translation options

In addition to the input file, output file, `source_lang` and `target_lang`
arguments, the available `translate_document()` and
`translate_document_from_filepath()` arguments are:

- `formality`: same as in [Text translation options](#text-translation-options).
- `glossary`: same as in [Text translation options](#text-translation-options).
- `glossary_ids`: same as in [Text translation options](#text-translation-options).
- `style_rule`: same as in [Text translation options](#text-translation-options).
- `translation_memory`: same as in [Text translation options](#text-translation-options).
- `translation_memory_threshold`: same as in [Text translation options](#text-translation-options).
- `output_format`: (`translate_document()` only)
  file extension of desired format of translated file, for example: `'pdf'`. If
  unspecified, by default the translated file will be in the same format as the
  input file. 

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
for more information. The entries should be specified as a dictionary.

If successful, the glossary is created and stored with your DeepL account, and
a `MultilingualGlossaryInfo` object is returned including the ID, name, and glossary
dictionaries. The glossary dictionaries would be an array of 
`MultilingualGlossaryDictionaryInfo` objects, each containing its own languages and 
entry count.

```python
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
the CSV data as `csv_data` either as a file-like object or string or bytes 
containing file content:

```python
# Open the CSV file assuming UTF-8 encoding. If your file contains a BOM,
# consider using encoding='utf-8-sig' instead.
with open('/path/to/glossary_file.csv', 'r',  encoding='utf-8') as csv_file:
    csv_data = csv_file.read()  # Read the file contents as a string
    my_csv_glossary = deepl_client.create_multilingual_glossary_from_csv(
        "CSV glossary",
        source_lang="EN",
        target_lang="DE",
        csv_data=csv_data,
    )
```

The [API documentation][api-docs-csv-format] explains the expected CSV format in
detail.

#### Getting, listing, and deleting stored glossaries

Functions to get, list, and delete stored glossaries are also provided:

- `get_multilingual_glossary()` takes a glossary ID and returns a 
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

To list the entries contained within a stored glossary, use
`get_multilingual_glossary_entries()` providing either the `MultilingualGlossaryInfo` object or glossary
ID and either a `MultilingualGlossaryDictionaryInfo` or source and target language pair:

```python
entries = deepl_client.get_multilingual_glossary_entries(my_glossary, "EN", "DE")
print(entries.dictionaries[0])  # "{'artist': 'Maler', 'prize': 'Gewinn'}"
```

#### Editing a glossary

Functions to edit stored glossaries are also provided:

- `update_multilingual_glossary_dictionary()` takes a glossary ID or `MultilingualGlossaryInfo`
  object, plus a source language, target language, and a dictionary of entries.
  It will then either update the list of entries for that dictionary (either 
  inserting new entires or replacing the target phrase for any existing 
  entries) or will insert a new glossary dictionary if that language pair is 
  not currently in the stored glossary.
- `replace_multilingual_glossary_dictionary()` takes a glossary ID or `MultilingualGlossaryInfo`
  object, plus a source language, target language, and a dictionary of entries.
  It will then either set the entries to the parameter value, completely 
  replacing any pre-existing entries for that language pair.
- `update_multilingual_glossary_name()` takes a glossary ID or `MultilingualGlossaryInfo`
  object, plus the new name of the glossary. 

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

entries_response = deepl_client.get_multilingual_glossary_entries(my_glossary, "EN", "DE")
print(entries_response.dictionaries[0])  # "{'artist': 'Maler', 'hello': 'hallo', 'prize': 'Gewinn'}"

# Update a glossary dictionary from CSV
# Open the CSV file assuming UTF-8 encoding. If your file contains a BOM,
# consider using encoding='utf-8-sig' instead.
with open('/path/to/glossary_file.csv', 'r',  encoding='utf-8') as csv_file:
    csv_data = csv_file.read()  # Read the file contents as a string
    my_csv_glossary = deepl_client.update_multilingual_glossary_dictionary_from_csv(
        glossary="4c81ffb4-2e...",
        source_lang="EN",
        target_lang="DE",
        csv_data=csv_data,
    )

# Replace glossary dictionary
replacement_entries = {"goodbye": "Auf Wiedersehen"}
glossary_dict = MultilingualGlossaryDictionaryEntries("EN", "DE", replacement_entries)
updated_glossary = deepl_client.replace_multilingual_glossary_dictionary(
  my_glossary,
  glossary_dict)
entries_response = deepl_client.get_multilingual_glossary_entries(my_glossary, "EN", "DE")
print(entries_response.dictionaries[0])  # "{'goodbye': 'Auf Wiedersehen'}"

# Replace a glossary dictionary from CSV
# Open the CSV file assuming UTF-8 encoding. If your file contains a BOM,
# consider using encoding='utf-8-sig' instead.
with open('/path/to/glossary_file.csv', 'r',  encoding='utf-8') as csv_file:
    csv_data = csv_file.read()  # Read the file contents as a string
    my_csv_glossary = deepl_client.replace_multilingual_glossary_dictionary_from_csv(
        glossary="4c81ffb4-2e...",
        source_lang="EN",
        target_lang="DE",
        csv_data=csv_data,
    )

# Update the glossary name
updated_glossary = deepl_client.update_multilingual_glossary_name(
  my_glossary,
  "My new glossary name"
)
print(updated_glossary.name) # 'My new glossary name'
```

#### Using a stored glossary

You can use a stored glossary for text translation by setting the `glossary`
argument to either the glossary ID or `GlossaryInfo`/`MultilingualGlossaryInfo` object.
You must also specify the `source_lang` argument (it is required when using a
glossary):

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

Using a stored glossary for document translation is the same: set the `glossary`
argument and specify the `source_lang` argument:

```python
deepl_client.translate_document(
    in_file, out_file, source_lang="EN", target_lang="DE", glossary=my_glossary,
)
```

The `translate_document()`, `translate_document_from_filepath()` and
`translate_document_upload()` functions all support the `glossary` argument.

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
the `any_limit_reached` property to check all usage subtypes.

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
`delete_style_rule_custom_instruction()` to manage them.

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

# Delete a custom instruction
deepl_client.delete_style_rule_custom_instruction(
    "YOUR_STYLE_ID", instruction.id
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

Importing takes a while: the API detects the uploaded file asynchronously, so
the job keeps reporting `awaiting_input` for roughly half a minute after the
upload before completing. Pass `timeout_s` to bound how long to wait.

The three steps are also available separately, for example to upload the file
yourself or to poll for progress. `create_translation_memory_import()` returns
an upload URL that the file must be uploaded to before processing starts, then
`get_translation_memory_job()` reports the status.

```python
created = deepl_client.create_translation_memory_import(
    file_name="legal.tmx",
    content_length=os.path.getsize("/path/to/legal.tmx"),
    display_name="Legal TM",
)
with open("/path/to/legal.tmx", "rb") as input_file:
    deepl_client.upload_translation_memory_file(created, input_file)

# The job reports "awaiting_input" both before the upload and for a while
# afterwards, until the API detects it; this polls through that status.
job = deepl_client.wait_until_translation_memory_job_done(
    created.job_id, timeout_s=300
)
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

### Writing a Plugin

If you use this library in an application, please identify the application with
`deepl.DeepLClient.set_app_info`, which needs the name and version of the app:

```python
deepl_client = deepl.DeepLClient(...).set_app_info("sample_python_plugin", "1.0.2")
```

This information is passed along when the library makes calls to the DeepL API.
Both name and version are required. Please note that setting the `User-Agent` header
via `deepl.http_client.user_agent` will override this setting, if you need to use this,
please manually identify your Application in the `User-Agent` header.

### Exceptions

All module functions may raise `deepl.DeepLException` or one of its subclasses.
If invalid arguments are provided, they may raise the standard exceptions
`ValueError` and `TypeError`.

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
argument when constructing a `deepl.DeepLClient`. This may be useful for testing
purposes. You **do not** need to specify the URL to distinguish API Free and API
Pro accounts, the library selects the correct URL automatically.

```python
server_url = "http://user:pass@localhost:3000"
deepl_client = deepl.DeepLClient(..., server_url=server_url)
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

#### Configure automatic retries

This SDK will automatically retry failed HTTP requests (if the failures could
be transient, e.g. a HTTP 429 status code). This behaviour can be configured
in `http_client.py`, for example by default the number of retries is 5. This
can be changed to 3 as follows:

```python
import deepl

deepl.http_client.max_network_retries = 3
c = deepl.DeepLClient(...)
c.translate_text(...)
```

You can configure the timeout `min_connection_timeout` the same way, as well
as set a custom `user_agent`, see the next section.

#### Anonymous platform information

By default, we send some basic information about the platform the client library is running on with each request, see [here for an explanation](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent). This data is completely anonymous and only used to improve our product, not track any individual users. If you do not wish to send this data, you can opt-out when creating your `deepl.DeepLClient` object by setting the `send_platform_info` flag like so:

```python
deepl_client = deepl.DeepLClient(..., send_platform_info=False)
```

You can also customize the `user_agent` by setting its value explicitly before constructing your `deepl.DeepLClient` object.

```python
deepl.http_client.user_agent = 'my custom user agent'
deepl_client = deepl.DeepLClient(os.environ["DEEPL_AUTH_KEY"])
```

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

Execute the tests using `pytest`. The tests communicate with the DeepL API using
the auth key defined by the `DEEPL_AUTH_KEY` environment variable.

Be aware that the tests make DeepL API requests that contribute toward your API
usage.

The test suite may instead be configured to communicate with the mock-server
provided by [deepl-mock][deepl-mock]. Although most test cases work for either,
some test cases work only with the DeepL API or the mock-server and will be
otherwise skipped. The test cases that require the mock-server trigger server
errors and test the client error-handling. To execute the tests using
deepl-mock, run it in another terminal while executing the tests. Execute the
tests using `pytest` with the `DEEPL_MOCK_SERVER_PORT` and `DEEPL_SERVER_URL`
environment variables defined referring to the mock-server.

[api-docs]: https://www.deepl.com/docs-api?utm_source=github&utm_medium=github-python-readme

[api-docs-csv-format]: https://www.deepl.com/docs-api/managing-glossaries/supported-glossary-formats/?utm_source=github&utm_medium=github-python-readme

[api-docs-xml-handling]: https://www.deepl.com/docs-api/handling-xml/?utm_source=github&utm_medium=github-python-readme

[api-docs-context-param]: https://www.deepl.com/docs-api/translating-text/?utm_source=github&utm_medium=github-python-readme

[api-docs-lang-list]: https://www.deepl.com/docs-api/translating-text/?utm_source=github&utm_medium=github-python-readme

[api-docs-glossary-lang-list]: https://www.deepl.com/docs-api/managing-glossaries/?utm_source=github&utm_medium=github-python-readme

[bug-report-ubuntu-2204]: https://bugs.launchpad.net/ubuntu/+source/poetry/+bug/1958227

[create-account]: https://www.deepl.com/pro?utm_source=github&utm_medium=github-python-readme#developer

[deepl-mock]: https://www.github.com/DeepLcom/deepl-mock

[issues]: https://www.github.com/DeepLcom/deepl-python/issues

[pypi-project]: https://pypi.org/project/deepl/

[pro-account]: https://www.deepl.com/pro-account/?utm_source=github&utm_medium=github-python-readme

[python-version-list]: https://devguide.python.org/versions/

[requests-proxy-docs]: https://docs.python-requests.org/en/latest/user/advanced/#proxies

[requests-verify-ssl-docs]: https://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification
