"""
title: Translate with TAG using the Retrieval Endpoint
author: Christian Lang & Anna Lackner (Kaleidoscope GmbH)
author_url: https://kaleidoscope.at
funding_url: https://kaleidoscope.at
version: 0.1
"""

import sys
import importlib

# sys.path.append("/app/backend/data/python_modules/kalcium-python-client")

sys.path.append(
    "/app/backend/data/python_modules/kalcium-python-client/src/kalcium_client"
)

import client  # kalcium_client
import kalcium_tag_functions as kalf

# import retrieval_endpoint_functions as ft

importlib.reload(client)
importlib.reload(kalf)
# importlib.reload(ft)

from pydantic import BaseModel, Field
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
import os
import requests
import json

# from lxml import etree as ET
import numpy as np
import re
from typing import List, Literal
from html import escape
from datetime import datetime
from time import sleep
from lxml import etree

load_dotenv(dotenv_path="/app/backend/data/python_modules/kalcium-python-client/.env")

kalciumBaseUrl = os.getenv("KALCIUM_BASE_URL_TAG_EVALUATION", "")
kalciumApiKey = os.getenv("KALCIUM_API_KEY_TAG_EVALUATION", "")
kalciumTermbaseIds = int(os.getenv("KALCIUM_TERMBASE_IDS_TAG_EVALUATION", "14"))
kalciumTenantId = int(os.getenv("KALCIUM_TENANT_ID_TAG_EVALUATION", "1"))

tag_formats = Literal["yaml", "markdown", "unchanged"]

supported_profile_Ids = Literal[7, 8, 15, 16, 17]


class Filter:
    class Valves(BaseModel):
        kalcium_base_url: str = Field(
            default=kalciumBaseUrl, description="Base-URL of Kalcium"
        )
        kalcium_api_key: str = Field(default=kalciumApiKey, description="API-key")
        termbaseIds: int = Field(
            default=kalciumTermbaseIds,
            description="Termbase ID",
            title="Termbase ID",
        )
        tenantId: int = Field(
            default=kalciumTenantId, title="Tenant ID", description="Kalcium Tenant ID"
        )
        pass

    class UserValves(BaseModel):
        show_tag_context: bool = Field(default=False, title="Show TAG context")
        show_citation: bool = Field(default=True, title="Show TAG citations")
        exact_matches: bool = Field(default=False, title="Consider exact matches only")
        tag_format: tag_formats = Field(default="markdown", title="TAG format")
        profileId: supported_profile_Ids = Field(
            default=17,
            title="Profile ID",
        )

        pass

    def __init__(self):
        # Indicates custom file handling logic. This flag helps disengage default routines in favor of custom
        # implementations, informing the WebUI to defer file-related operations to designated methods within this class.
        # Alternatively, you can remove the files directly from the body in from the inlet hook
        # self.file_handler = True

        # Initialize 'valves' with specific configurations. Using 'Valves' instance helps encapsulate settings,
        # which ensures settings are managed cohesively and not confused with operational flags like 'file_handler'.
        self.valves = self.Valves()

        self.language_map = {
            "german": 352,
            "english": 306,
            "czech": 318,
            "italian": 309,
        }
        self.language_abbreviation_map = {
            352: "de-at",
            306: "en-gb",
            318: "cs",
            309: "it-it",
        }

        self.value_map = {
            17: {
                "language_names": {
                    "german": 314,
                    "english": 306,
                },
                "languages": {306: "en-gb", 314: "de-de"},
                "usage_status": {
                    "name": "usageStatus",
                    "preferred": "preferred",
                    "allowed": "admitted",
                    "forbidden": "deprecated",
                },
                "definition": {"name": "definition", "level": "language"},
                "usage_note": {
                    "name": "note",
                },
            },
            7: {
                "language_names": {
                    "german": 352,
                    "english": 306,
                    "czech": 318,
                    "italian": 309,
                },
                "languages": {306: "en-gb", 352: "de-at", 318: "cs", 309: "it-it"},
                "usage_status": {
                    "name": "Usage",
                    "preferred": "Preferred",
                    "allowed": "Allowed",
                    "forbidden": "Forbidden",
                },
                "definition": {"name": "definition", "level": "concept"},
                "usage_note": {
                    "name": "usage note",
                },
            },
            8: {
                "language_names": {
                    "german": 352,
                    "english": 306,
                    "czech": 318,
                    "italian": 309,
                },
                "languages": {306: "en-gb", 352: "de-at", 318: "cs", 309: "it-it"},
                "usage_status": {
                    "name": "Usage",
                    "allowed": "Allowed",
                    "forbidden": "Forbidden",
                },
                "definition": {"name": "definition", "level": "concept"},
                "usage_note": {
                    "name": "usage note",
                },
            },
            15: {
                "language_names": {
                    "german": 352,
                    "english": 306,
                    "czech": 318,
                    "italian": 309,
                },
                "languages": {306: "en-gb", 352: "de-at", 318: "cs", 309: "it-it"},
                "usage_status": {
                    "name": "Usage",
                    "allowed": "Allowed",
                    "forbidden": "Forbidden",
                },
                "definition": {"name": "definition", "level": "concept"},
                "usage_note": {
                    "name": "usage note",
                },
            },
            16: {
                "language_names": {
                    "german": 352,
                    "english": 306,
                    "czech": 318,
                    "italian": 309,
                },
                "languages": {306: "en-gb", 352: "de-at", 318: "cs", 309: "it-it"},
                "usage_status": {
                    "name": "Usage",
                    "allowed": "Allowed",
                    "forbidden": "Forbidden",
                },
                "definition": {"name": "definition", "level": "concept"},
                "usage_note": {
                    "name": "usage note",
                },
            },
        }

        baseUrl = self.valves.kalcium_base_url
        tenantId = self.valves.tenantId
        urlToken = self.valves.kalcium_api_key

        self.kalc = client.KalciumClient(
            baseUrl, tenantId, urlToken=urlToken, getAliases=True
        )

        pass

    async def inlet(
        self, body: dict, __user__: Optional[dict] = None, __event_emitter__=None
    ) -> dict:
        # Modify the request body or validate it before processing by the chat completion API.
        # This function is the pre-processor for the API where various checks on the input can be performed.
        # It can also modify the request before sending it to the API.
        print(f"inlet:{__name__}")
        print(f"inlet:body:{body}")
        print(f"inlet:user:{__user__}")

        if __user__.get("role", "admin") in ["user", "admin"]:
            messages = body.get("messages", [])

            # get user valves
            user_valves = __user__.get("valves")
            if not user_valves:
                user_valves = self.UserValves()
            profileId = user_valves.profileId
            tag_format = user_valves.tag_format
            exact_matches_only = user_valves.exact_matches

            # Get language direction from prompt
            languages = []
            for word in messages[-1]["content"].split(":")[0].split():
                if word.lower() in self.value_map[profileId]["language_names"].keys():
                    if word.lower() not in languages:
                        languages.append(word.lower())
            if len(languages) < 2:
                raise ValueError(
                    """Please provide one source and one target language in the following format: Translate from {source} to {target}: \n
                Supported languages: German, English"""
                )
            else:
                self.sourceLanguage = languages[0]
                self.kalc.sourceLanguageIds = [
                    self.value_map[profileId]["language_names"][self.sourceLanguage]
                ]
                self.targetLanguage = languages[1]
                self.kalc.targetLanguageIds = [
                    self.value_map[profileId]["language_names"][self.targetLanguage]
                ]

            # Inform user about TAG taking place
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Retrieving terminology...",
                        "done": False,
                    },
                }
            )

            # perform tag
            # try:
            translation, entries = find_translation(
                self.kalc,
                ":".join(messages[-1]["content"].split(":")[1:]),
                profileId,
                self.kalc.sourceLanguageIds,
                self.kalc.targetLanguageIds,
                self.value_map,
                tag_format=tag_format,
                exact_matches_only=exact_matches_only,
            )
            # except Exception as e:
            #    raise Exception(f"Error retrieving terms: {e}")

            # add tag context to prompt
            if translation:  # and entries:
                messages[-1]["content"] = (
                    f"<tag>\n{translation}\n</tag>\n\n" + messages[-1]["content"]
                )
                # Output message that Retrieval is done.
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Found {len(entries)} concept{'s' if len(entries) != 1 else ''}.",  # f"Found concepts",
                            "done": True,
                        },
                    }
                )
            else:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "No terminology found.", "done": True},
                    }
                )

            if user_valves.show_citation:
                for key in entries.keys():
                    await __event_emitter__(
                        {
                            "type": "citation",
                            "data": {
                                "document": [
                                    kalf.kalcium_tag_format(
                                        {key: entries[key]},
                                        task="translation",
                                        format=tag_format,
                                        add_codeblock=False,
                                    ),
                                ],
                                "metadata": [
                                    {
                                        "date_accessed": datetime.now().isoformat(),
                                        "source": f"#{key} ({[term for term in entries[key]['terms']][0]})",
                                    }
                                ],
                                "source": {
                                    "name": f"#{key} ({[term for term in entries[key]['terms']][0]})",
                                    "url": f"{self.valves.kalcium_base_url}/terminology/search?entryId={key}&termbaseId={self.valves.termbaseIds}",
                                },
                            },
                        },
                    )

            for message in messages:
                if "\n\n### TAG context:\n" in message["content"]:
                    message["content"] = message["content"].split(
                        "\n\n### TAG context:\n"
                    )[0]

            self.kalc.tag_context = translation

        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # Modify or analyze the response body after processing by the API.
        # This function is the post-processor for the API, which can be used to modify the response
        # or perform additional checks and analytics.
        print(f"outlet:{__name__}")
        print(f"outlet:body:{body}")
        print(f"outlet:user:{__user__}")

        messages = body.get("messages", [])

        # get user valves
        user_valves = __user__.get("valves")
        if not user_valves:
            user_valves = self.UserValves()
        if user_valves.show_tag_context:
            tag_context = self.kalc.tag_context
            messages[-1]["content"] = (
                messages[-1]["content"] + "\n\n### TAG context:\n" + str(tag_context)
            )

        return body


# -----------------------------------
def get_entries_xml(search_results, sourceLanguageId, targetLanguageId):
    if not search_results:
        return None
    try:
        root = etree.fromstring(search_results)
    except Exception as e:
        raise Exception(str(f"Invalid XML Format: {str(e)}"))

    entry_dict = {}
    for e in root.findall(".//e"):
        # get entry id
        entry_id = e.find("id").get("id") if e.find("id") is not None else None
        if entry_id and entry_id not in entry_dict.keys():
            entry_dict[entry_id] = {"terms": {}, "fields": {}}
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
                l_field_name = f.get("n")
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
                    entry_dict[entry_id]["fields"][field] = language_fields[
                        sourceLanguageId
                    ][field]
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


def get_entries_json(
    search_results: list,
    sourceLanguageId: int,
    targetLanguageId: int,
    language_map: dict,
    profileId: int,
    value_map: dict,
):
    if not search_results:
        return None

    entry_dict = {}
    for idx, entry in enumerate(search_results):
        if value_map[profileId]["definition"]["level"] == "concept":
            definition = get_info(entry, value_map[profileId]["definition"]["name"])
        elif value_map[profileId]["definition"]["level"] == "language":
            definition = get_info(
                entry,
                f"{language_map[targetLanguageId]}_"
                + value_map[profileId]["definition"]["name"],
            )
            if definition is None:
                definition = get_info(
                    entry,
                    f"{language_map[sourceLanguageId]}_"
                    + value_map[profileId]["definition"]["name"],
                )
        source_terms = []
        target_terms = []
        for i, term in enumerate(entry):
            source_term = get_info(
                entry, f"{language_map[sourceLanguageId]}_term_{i+1}"
            )
            if (
                source_term
                and get_info(
                    entry,
                    f"{language_map[sourceLanguageId]}_term_{i+1}_"
                    + value_map[profileId]["usage_status"]["name"],
                )
                != value_map[profileId]["usage_status"]["forbidden"]
            ):
                source_terms.append(source_term)
            target_term = get_info(
                entry, f"{language_map[targetLanguageId]}_term_{i+1}"
            )
            usage_note = get_info(
                entry,
                f"{language_map[targetLanguageId]}_term_{i+1}_"
                + value_map[profileId]["usage_note"]["name"],
            )
            usage_status = get_info(
                entry,
                f"{language_map[targetLanguageId]}_term_{i+1}_"
                + value_map[profileId]["usage_status"]["name"],
            )
            if target_term:
                target_dict = {target_term: {}}
                if usage_note:
                    target_dict[target_term]["usage_note"] = usage_note
                if usage_status:
                    target_dict[target_term]["usage_status"] = usage_status
                target_terms.append(target_dict)
        if idx not in entry_dict.keys():
            entry_dict[idx] = {"terms": {}, "fields": {}}

        if source_terms[0] not in entry_dict[idx]["terms"].keys():
            entry_dict[idx]["terms"][source_terms[0]] = []
        entry_dict[idx]["terms"][source_terms[0]].extend(target_terms)
        if definition:
            entry_dict[idx]["fields"] = {"definition": definition}
    return entry_dict


def find_translation(
    kalc,
    text: str,
    profileId: int,
    sourceLanguageIds: List,
    targetLanguageIds: List,
    value_map: dict,
    tag_format: str = "markdown",
    exact_matches_only: bool = False,
):
    if not text:
        raise Exception("Text cannot be empty")
    if profileId < 0:
        raise Exception("Invalid profile ID")

    entries = {}
    try:
        search_results = kalc.get_entry_content_by_lang_id(
            text, profileId, sourceLanguageIds, targetLanguageIds
        )
    except Exception as e:
        print("Error retrieving terms", e)
        raise Exception(str(e) + text)
    # Return search results as unchanged text or convert to Dictionary from XML/JSON
    if tag_format == "unchanged":
        return (
            search_results
            if search_results
            else "No information found in the termbase."
        ), {}
    if isinstance(search_results, str):
        entries = get_entries_xml(
            search_results, sourceLanguageIds[0], targetLanguageIds[0]
        )
    elif isinstance(search_results, list):
        entries = get_entries_json(
            search_results,
            sourceLanguageIds[0],
            targetLanguageIds[0],
            value_map[profileId]["languages"],
            profileId,
            value_map,
        )

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
                        if (
                            term[field][value_map[profileId]["usage_status"]["name"]]
                            != value_map[profileId]["usage_status"]["forbidden"]
                        ):
                            final_entries[entry_id]["terms"][concept].append(term)
            final_entries[entry_id]["fields"] = entries[entry_id]["fields"]
        entries = final_entries
        if not entries:
            return "```markdown\nNo information found in the termbase.\n```", {}
    except KeyError:
        pass

    # checking for exact matches
    # if exact_matches_only:
    #    exact_matches = {}
    #    for entry_id in entries:
    #        term = (next(iter(entries[entry_id]["terms"])))
    #        if term in text:
    #            exact_matches[entry_id] = entries[entry_id]
    #    entries = exact_matches

    return (
        kalf.kalcium_tag_format(entries, task="translation", format=tag_format),
        entries,
    )


def check_terminology(
    kalc,
    text: str,
    profileId: int,
    sourceLanguageIds: List,
    targetLanguageIds: List,
    value_map: dict,
    tag_format: str = "markdown",
    exact_matches_only: bool = False,
):
    if not text:
        raise Exception("Text cannot be empty")
    if profileId < 0:
        raise Exception("Invalid profile ID")
    if sourceLanguageIds[0] != targetLanguageIds[0]:
        raise Exception(
            "Differing source and target language ID for monolingual term revision"
        )

    entries = {}
    try:
        search_results = kalc.get_entry_content_by_lang_id(
            text, profileId, sourceLanguageIds, targetLanguageIds
        )
    except Exception as e:
        print("Error retrieving terms", e)
        raise Exception(str(e) + text)
    if isinstance(search_results, str):
        entries = get_entries_xml(
            search_results, sourceLanguageIds[0], targetLanguageIds[0]
        )
    elif isinstance(search_results, list):
        entries = get_entries_json(
            search_results,
            sourceLanguageIds[0],
            targetLanguageIds[0],
            value_map[profileId]["languages"],
            profileId,
            value_map,
        )

    if not entries:
        return "```markdown\nNo information found in the termbase.\n```", {}

    def add_usage(entries: dict, entry: dict, term: str, type: str):
        try:
            if (
                entry[value_map[profileId]["usage_status"]["name"]]
                == value_map[profileId]["usage_status"][type]
            ):
                if f"{type} terms" not in entries.keys():
                    entries[f"{type} terms"] = []
                term_dict = {term: {}}
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
                    add_usage(
                        final_entries[entry_id]["terms"][concept],
                        term[field],
                        field,
                        "preferred",
                    )
                    add_usage(
                        final_entries[entry_id]["terms"][concept],
                        term[field],
                        field,
                        "allowed",
                    )
                    add_usage(
                        final_entries[entry_id]["terms"][concept],
                        term[field],
                        field,
                        "forbidden",
                    )
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

    return (
        kalf.kalcium_tag_format(final_entries, task="revision", format=tag_format),
        final_entries,
    )
