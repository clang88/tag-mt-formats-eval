from typing import List
from lxml import etree

from . import kalcium_tag_functions as kalf

# getting entries using xml retrieval profile
def get_entries_xml(search_results, sourceLanguageId, targetLanguageId):
    if not search_results:
        return None
    try:
        root = etree.fromstring(search_results)
    except Exception as e:
        raise Exception(str(f"Invalid XML Format: {str(e)}"))

    entry_dict = {}
    for e in root.findall('.//e'):
        # get entry id
        entry_id = e.find("id").get("id") if e.find("id") is not None else None
        if entry_id and entry_id not in entry_dict.keys():
            entry_dict[entry_id] = {"terms" : {}, "fields" : {}}
        # get all entry level fields
        for f in e.findall("f"):
            e_field_name = f.get("n")
            e_field_content = f.get("v")
            if e_field_name is not None:
                if e_field_name not in entry_dict[entry_id]["fields"].keys():
                    entry_dict[entry_id]["fields"][e_field_name] = e_field_content

        # get all language and term level fields
        target_terms = []
        source_terms = []
        language_fields = {}
        for l in e.findall("l"):
            lid = l.attrib["lid"]
            # get all language level fields
            language_fields[int(lid)] = {}
            for f in l.findall("f"):
                l_field_name = f.get ("n")
                l_field_content = f.get("v")
                if l_field_name not in language_fields[int(lid)].keys():
                    language_fields[int(lid)][l_field_name] = l_field_content
            # get all terms
            for t in l.findall("t"):
                term_dict = {}
                term = t.attrib["t"]
                if term not in term_dict.keys():
                    term_dict[term] = {}

                # get all term level fields
                for f in t.findall("f"):
                    t_field_name = f.get("n")
                    t_field_content = f.get("v")
                    if t_field_name not in term_dict[term].keys():
                        term_dict[term][t_field_name] = t_field_content
                if int(lid) == targetLanguageId:
                    target_terms.append(term_dict)
                elif int(lid) == sourceLanguageId:
                    source_terms.append(term)

        if sourceLanguageId == targetLanguageId:
            source_terms.append(next(iter(target_terms[0].keys())))
        # add target language fields
        try: 
            entry_dict[entry_id]["fields"].update(language_fields[targetLanguageId])
            # add source language fields if they don't exist as target fields
            for field in language_fields[sourceLanguageId]:
                if field not in entry_dict[entry_id]["fields"].keys():
                    entry_dict[entry_id]["fields"][field] = language_fields[sourceLanguageId][field]
            # add term fields
            entry_dict[entry_id]["terms"][source_terms[0]] = target_terms
        except KeyError:
            entry_dict.pop(entry_id)
    return entry_dict

# helper for json retrieval profile function
def get_info(entry: dict, field: str):
    try:
        return entry[field]
    except KeyError:
        return None
    
def get_entries_json(search_results:list, sourceLanguageId:int, targetLanguageId:int, language_map:dict, profileId:int, value_map:dict):
    if not search_results:
        return None
    
    entry_dict = {}
    for idx, entry in enumerate(search_results):
        if value_map[profileId]["definition"]["level"] == "concept":
            definition = get_info(entry, value_map[profileId]["definition"]["name"])
        elif value_map[profileId]["definition"]["level"] == "language":
            definition = get_info(entry, f"{language_map[targetLanguageId]}_"+value_map[profileId]["definition"]["name"])
            if definition is None:
                definition = get_info(entry, f"{language_map[sourceLanguageId]}_"+value_map[profileId]["definition"]["name"])
        source_terms = []
        target_terms = []
        for i, term in enumerate(entry):
            source_term = get_info(entry, f"{language_map[sourceLanguageId]}_term_{i+1}")
            if source_term and get_info(entry, f"{language_map[sourceLanguageId]}_term_{i+1}_" + value_map[profileId]["usage_status"]["name"]) != value_map[profileId]["usage_status"]["forbidden"]:
                source_terms.append(source_term)
            target_term = get_info(entry, f"{language_map[targetLanguageId]}_term_{i+1}")
            usage_note = get_info(entry, f"{language_map[targetLanguageId]}_term_{i+1}_" + value_map[profileId]["usage_note"]["name"])
            usage_status = get_info(entry, f"{language_map[targetLanguageId]}_term_{i+1}_" + value_map[profileId]["usage_status"]["name"])
            if target_term:
                target_dict = {target_term : {}}
                if usage_note:
                    target_dict[target_term]["usage_note"] = usage_note
                if usage_status:
                    target_dict[target_term]["usage_status"] = usage_status
                target_terms.append(target_dict)
        if idx not in entry_dict.keys():
            entry_dict[idx] = {"terms" : {}, "fields" : {}}

        if source_terms[0] not in entry_dict[idx]["terms"].keys():
            entry_dict[idx]["terms"][source_terms[0]] = []
        entry_dict[idx]["terms"][source_terms[0]].extend(target_terms)
        if definition:
            entry_dict[idx]["fields"] = {"definition" : definition}
    return entry_dict


def find_translation(kalc, text:str, profileId:int, sourceLanguageIds:List, targetLanguageIds:List, value_map:dict, tag_format:str="markdown", exact_matches_only:bool=False):
    if not text:
        raise Exception("Text cannot be empty")
    if profileId < 0:
        raise Exception("Invalid profile ID")

    entries = {}
    try:
        search_results = kalc.get_entry_content_by_lang_id(text, profileId, sourceLanguageIds, targetLanguageIds)
    except Exception as e:
        print("Error retrieving terms", e)
        raise Exception(str(e) + text)
    # Return search results as unchanged text or convert to Dictionary from XML/JSON
    if tag_format == "unchanged":
        return search_results if search_results else "No information found in the termbase.", {}
    if isinstance(search_results, str):
        entries = get_entries_xml(search_results, sourceLanguageIds[0], targetLanguageIds[0])
    elif isinstance(search_results, list):
        entries = get_entries_json(search_results, sourceLanguageIds[0], targetLanguageIds[0], value_map[profileId]["languages"], profileId, value_map)

    if not entries:
        return "```markdown\nNo information found in the termbase.\n```", {}

    # removing forbidden terms (in case usage status is enabled)
    try:
        final_entries = {}
        for entry_id in entries.keys():
            final_entries[entry_id] = {}
            for concept in entries[entry_id]["terms"].keys():
                final_entries[entry_id]["terms"] = {}
                final_entries[entry_id]["terms"][concept] = []
                for term in entries[entry_id]["terms"][concept]:
                    for field in term.keys():
                        if term[field][value_map[profileId]["usage_status"]["name"]] != value_map[profileId]["usage_status"]["forbidden"]:
                            final_entries[entry_id]["terms"][concept].append(term)
            final_entries[entry_id]["fields"] = entries[entry_id]["fields"]
        entries = final_entries
        if not entries:
            return "```markdown\nNo information found in the termbase.\n```", {}
    except KeyError:
        pass
    
    # checking for exact matches
    #if exact_matches_only:
    #    exact_matches = {}
    #    for entry_id in entries:
    #        term = (next(iter(entries[entry_id]["terms"])))
    #        if term in text:
    #            exact_matches[entry_id] = entries[entry_id]
    #    entries = exact_matches

    return kalf.kalcium_tag_format(entries, task="translation", format=tag_format), entries

def check_terminology(kalc, text: str, profileId: int, sourceLanguageIds: List, targetLanguageIds: List, value_map: dict,
                     tag_format: str = "markdown", exact_matches_only: bool = False):
    if not text:
        raise Exception("Text cannot be empty")
    if profileId < 0:
        raise Exception("Invalid profile ID")
    if sourceLanguageIds[0] != targetLanguageIds[0]:
        raise Exception("Differing source and target language ID for monolingual term revision")

    entries = {}
    try:
        search_results = kalc.get_entry_content_by_lang_id(text, profileId, sourceLanguageIds, targetLanguageIds)
    except Exception as e:
        print("Error retrieving terms", e)
        raise Exception(str(e) + text)
    if isinstance(search_results, str):
        entries = get_entries_xml(search_results, sourceLanguageIds[0], targetLanguageIds[0])
    elif isinstance(search_results, list):
        entries = get_entries_json(search_results, sourceLanguageIds[0], targetLanguageIds[0],
                                   value_map[profileId]["languages"], profileId, value_map)

    if not entries:
        return "```markdown\nNo information found in the termbase.\n```", {}

    def add_usage(entries:dict, entry:dict, term:str, type:str):
        try:
            if entry[value_map[profileId]["usage_status"]["name"]] == value_map[profileId]["usage_status"][type]:
                if f"{type} terms" not in entries.keys():
                    entries[f"{type} terms"] = []
                term_dict = {term : {}}
                for field in entry.keys():
                    if field != value_map[profileId]["usage_status"]["name"]:
                        term_dict[term][field] = entry[field]
                entries[f"{type} terms"].append(term_dict)
        except KeyError:
            pass

    # building the final entries for the revision function
    final_entries = {}
    for entry_id in entries.keys():
        final_entries[entry_id] = {}
        for concept in entries[entry_id]["terms"].keys():
            final_entries[entry_id]["terms"] = {}
            final_entries[entry_id]["terms"][concept] = {}
            for term in entries[entry_id]["terms"][concept]:
                for field in term.keys():
                    add_usage(final_entries[entry_id]["terms"][concept], term[field], field, "preferred")
                    add_usage(final_entries[entry_id]["terms"][concept], term[field], field, "allowed")
                    add_usage(final_entries[entry_id]["terms"][concept], term[field], field, "forbidden")
        final_entries[entry_id]["fields"] = entries[entry_id]["fields"]
    if not final_entries:
        return "```markdown\nNo information found in the termbase.\n```", {}

    # checking for exact matches
    # if exact_matches_only:
    #    exact_matches = {}
    #    for entry_id in entries:
    #        term = (next(iter(entries[entry_id]["terms"])))
    #        if term in text:
    #            exact_matches[entry_id] = entries[entry_id]
    #    entries = exact_matches

    return kalf.kalcium_tag_format(final_entries, task="revision", format=tag_format), final_entries
