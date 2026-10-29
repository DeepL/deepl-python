# Migration Documentation for Newest Glossary Functionality

## 1. Overview of Changes
The newest version of the Glossary APIs is the `/v3` endpoints, which introduce enhanced functionality:
- **Support for Multilingual Glossaries**: The v3 endpoints allow for the creation of glossaries with multiple language pairs, enhancing flexibility and usability.
- **Editing Capabilities**: Users can now edit existing glossaries.

To support these new v3 APIs, we have created new methods to interact with these new multilingual glossaries. Users are encouraged to transition to the new to take full advantage of these new features. The `v2` methods for monolingual glossaries (e.g., `create_glossary()`, `get_glossary()`, etc.) remain available, however users are encouraged to update to use the new functions.

## 2. Endpoint Changes

| Monolingual glossary methods         | Multilingual glossary methods        | Changes Summary                                           |
|--------------------------------------|--------------------------------------|----------------------------------------------------------|
| `create_glossary()`                  | `create_multilingual_glossary()`              | Accepts a list of `MultilingualGlossaryDictionaryEntries` for multi-lingual support and now returns a `MultilingualGlossaryInfo` object. |
| `create_glossary_from_csv()`         | `create_multilingual_glossary_from_csv()`     | Similar functionality, but now returns a `MultilingualGlossaryInfo` object |
| `get_glossary()`                     | `get_multilingual_glossary()`                 | Similar functionality, but now returns `MultilingualGlossaryInfo`. Also can accept a `MultilingualGlossaryInfo` object as the glossary parameter instead of a `GlossaryInfo` object.|
| `list_glossaries()`                  | `list_multilingual_glossaries()`              | Similar functionality, but now returns a list of `MultilingualGlossaryInfo` objects.        |
| `get_glossary_entries()`             | `get_multilingual_glossary_dictionary_entries()` | Requires specifying source and target languages. Returns a `MultilingualGlossaryDictionaryEntries` object whose `entries` is a dictionary. (`get_multilingual_glossary_entries()` is deprecated.) |
| `delete_glossary()`                  | `delete_multilingual_glossary()`              | Similar functionality, but now can accept a `MultilingualGlossaryInfo` object instead of a `GlossaryInfo` object when specifying the glossary.  |

## 3. Model Changes
V2 glossaries are monolingual and the previous glossary objects could only have entries for one language pair (`source_lang` and `target_lang`). Now we introduce the concept of "glossary dictionaries", where a glossary dictionary specifies its own `source_lang`, `target_lang`, and has its own entries.

- **Glossary Information**:
  - **v2**: `GlossaryInfo` supports only mono-lingual glossaries, containing fields such as `source_lang`, `target_lang`, and `entry_count`.
  - **v3**: `MultilingualGlossaryInfo` supports multi-lingual glossaries and includes a list of `MultilingualGlossaryDictionaryInfo`, which provides details about each glossary dictionary, each with its own `source_lang`, `target_lang`, and `entry_count`.

- **Glossary Entries**:
  - **v3**: Introduces `MultilingualGlossaryDictionaryEntries`, which encapsulates a glossary dictionary wiht source and target languages along with its entries.

## 4. Code Examples

### Create a glossary

```python
# monolingual glossary example
glossary_info = deepl_client.create_glossary("My Glossary", "EN", "DE", {"hello": "hallo"})

# multilingual glossary example
glossary_dicts = [MultilingualGlossaryDictionaryEntries("EN", "DE", {"hello": "hallo"})]
glossary_info = deepl_client.create_multilingual_glossary("My Glossary", glossary_dicts)
```
### Get a glossary
```python
# monolingual glossary example
created_glossary = deepl_client.create_glossary("My Glossary", "EN", "DE", {"hello": "hallo"})
glossary_info = deepl_client.get_glossary(created_glossary) # GlossaryInfo object

# multilingual glossary example
glossary_dicts = [MultilingualGlossaryDictionaryEntries("EN", "DE", {"hello": "hallo"})]
created_glossary = deepl_client.create_multilingual_glossary("My Glossary", glossary_dicts)
glossary_info = deepl_client.get_multilingual_glossary(created_glossary) # MultilingualGlossaryInfo object
```

### Get glossary entries
```python
# monolingual glossary example
created_glossary = deepl_client.create_glossary("My Glossary", "EN", "DE", {"hello": "hallo"})
entries = deepl_client.get_glossary_entries(created_glossary)
print(entries) # 'hello\thallo'

# multilingual glossary example
glossary_dicts = [MultilingualGlossaryDictionaryEntries("EN", "DE", {"hello": "hallo"})]
created_glossary = deepl_client.create_multilingual_glossary("My Glossary", glossary_dicts)
dict_entries = deepl_client.get_multilingual_glossary_dictionary_entries(created_glossary, "EN", "DE")
print(dict_entries.entries) # {'hello': 'hallo'}
```

### List and delete glossaries
```python
# monolingual glossary example
glossaries = deepl_client.list_glossaries()
for glossary in glossaries:
    if glossary.name == "Old glossary":
        deepl_client.delete_glossary(glossary)

# multilingual glossary example
glossaries = deepl_client.list_multilingual_glossaries()
for glossary in glossaries:
    if glossary.name == "Old glossary":
        deepl_client.delete_multilingual_glossary(glossary)
```


## 5. New Multilingual Glossary Methods

In addition to introducing multilingual glossaries, we introduce several new methods that enhance the functionality for managing glossaries. Below are the details for each new method:

### Update Multilingual Glossary Dictionary
- **Method**: `update_multilingual_glossary_dictionary(glossary: Union[str, MultilingualGlossaryInfo], dictionary: MultilingualGlossaryDictionaryEntries) -> MultilingualGlossaryInfo`
- **Description**: Use this method to update or create a glossary dictionary's entries
- **Parameters**:
  - `glossary`: The ID or `MultilingualGlossaryInfo` of the glossary to update.
  - `dictionary`: The glossary dictionary including its new entries.
- **Returns**: `MultilingualGlossaryInfo` containing information about the updated glossary.
- **Note**: This method will either update the glossary's entries if they exist for the given glossary dictionary's language pair, or adds any new ones to the dictionary if not. It will also create a new glossary dictionary if one
did not exist for the given language pair.
- **Example**:
```python
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
```

### Update Multilingual Glossary Dictionary from CSV
- **Method**: `update_multilingual_glossary_dictionary_from_csv(glossary: Union[str, MultilingualGlossaryInfo], source_lang: Union[str, Language], target_lang: Union[str, Language], csv: Union[TextIO, BinaryIO, str, bytes, Any]) -> MultilingualGlossaryInfo`
- **Description**: This method allows you to update or create a glossary dictionary using entries in CSV format.
- **Parameters**:
  - `glossary`: The ID or `MultilingualGlossaryInfo` of the glossary to update.
  - `source_lang`: Language of source entries.
  - `target_lang`: Language of target entries.
  - `csv`: CSV data containing glossary entries.
- **Returns**: `MultilingualGlossaryInfo` containing information about the updated glossary.
- **Example**:
  ```python
    # Replace a glossary dictionary from CSV
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

### Update Multilingual Glossary Name
- **Method**: `update_multilingual_glossary_name(glossary: Union[str, MultilingualGlossaryInfo], name: str) -> MultilingualGlossaryInfo`
- **Description**: This method allows you to update the name of an existing glossary.
- **Parameters**:
  - `glossary`: The ID or `MultilingualGlossaryInfo` of the glossary to update.
  - `name`: The new name for the glossary.
- **Returns**: `MultilingualGlossaryInfo` containing information about the updated glossary.
- **Example**:
  ```python
  updated_glossary = deepl_client.update_multilingual_glossary_name("4c81ffb4-2e...", "New Glossary Name")

### Replace a Multilingual Glossary Dictionary
- **Method**: `replace_multilingual_glossary_dictionary(glossary: Union[str, MultilingualGlossaryInfo], dictionary: MultilingualGlossaryDictionaryEntries) -> MultilingualGlossaryInfo`
- **Description**: This method replaces the existing glossary dictionary with a new set of entries.
- **Parameters**:
  - `glossary`: The ID or `MultilingualGlossaryInfo` of the glossary whose dictionary will be replaced.
  - `dictionary`: The new glossary dictionary entries that will replace any existing ones for that language pair.
- **Returns**: `MultilingualGlossaryInfo` containing information about the updated glossary.
- **Note**: Ensure that the new dictionary entries are complete and valid, as this method will completely overwrite the existing entries. It will also create a new glossary dictionary if one did not exist for the given language pair.
- **Example**:
  ```python
  new_glossary_dict = MultilingualGlossaryDictionaryEntries("EN", "DE", {"goodbye": "auf Wiedersehen"})
  replaced_glossary = deepl_client.replace_multilingual_glossary_dictionary("4c81ffb4-2e...", new_glossary_dict)

### Replace Multilingual Glossary Dictionary from CSV
- **Method**: `replace_multilingual_glossary_dictionary_from_csv(glossary: Union[str, MultilingualGlossaryInfo], source_lang: Union[str, Language], target_lang: Union[str, Language], csv: Union[TextIO, BinaryIO, str, bytes, Any]) -> MultilingualGlossaryInfo`
- **Description**: This method allows you to replace or create a glossary dictionary using entries in CSV format.
- **Parameters**:
  - `glossary`: The ID or `MultilingualGlossaryInfo` of the glossary to update.
  - `source_lang`: Language of source entries.
  - `target_lang`: Language of target entries.
  - `csv`: CSV data containing glossary entries.
- **Returns**: `MultilingualGlossaryInfo` containing information about the updated glossary.
- **Example**:
  ```python
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

### Delete a Multilingual Glossary Dictionary
- **Method**: `delete_multilingual_glossary_dictionary(glossary: Union[str, MultilingualGlossaryInfo], dictionary: Optional[MultilingualGlossaryDictionaryInfo] = None, source_lang: Optional[str] = None, target_lang: Optional[str] = None) -> None`
- **Description**: This method deletes a specified glossary dictionary from a given glossary.
- **Parameters**:
  - `glossary`: The ID or `MultilingualGlossaryInfo` of the glossary containing the dictionary to delete.
  - `dictionary`: An optional parameter that specifies the dictionary to delete. This can be a `MultilingualGlossaryDictionaryInfo` object or both `source_lang` and `target_lang` to identify the dictionary.
  - `source_lang`: An optional parameter representing the source language of the dictionary.
  - `target_lang`: An optional parameter representing the target language of the dictionary.
- **Returns**: None
  
- **Migration Note**: Ensure that your application logic correctly identifies the dictionary to delete. If using `source_lang` and `target_lang`, both must be provided to specify the dictionary.
  
- **Example**:
  ```python
  glossary_dict_deen = MultilingualGlossaryDictionaryEntries("EN", "DE", {"hello": "hallo"})
  glossary_dict_ende = MultilingualGlossaryDictionaryEntries("DE", "EN", {"hallo": "hello"})
  glossary_dicts = [glossary_dict_deen, glossary_dict_ende]
  created_glossary = deepl_client.create_multilingual_glossary("My Glossary", glossary_dicts)

  # Delete via specifying the glossary dictionary
  deepl_client.delete_multilingual_glossary_dictionary(created_glossary, created_glossary.dictionaries[0])

  # Delete via specifying the language pair
  deepl_client.delete_multilingual_glossary_dictionary(created_glossary, source_lang="DE", target_lang="EN")
  ```