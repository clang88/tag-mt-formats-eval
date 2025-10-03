from typing import List
import requests
import json
import re
from html import escape
# Troubleshooting
import traceback 
import sys

from urllib.parse import quote

# Todo: 
# * Change "print" statements to "logging"
# * Create proper field + value mapping function that can be optionally used by all search/analyze functions 


class KalciumClient:
    def __init__(self, baseUrl: str, tenantId: int, user:str = "", password:str = "",
                 urlToken:str = "", getAliases: bool = False):
        """Initialize the Kalcium client.

        This constructor sets up the Kalcium client with the specified parameters,
        including authenticating the user via a URL token or standard login via Username + PW.

        Parameters
        ----------
        
        baseUrl : str, mandatory
            base URL for Kalcium API, e.g. "https://trial.kalcium.cloud/"
        tenantId : int, mandatory                                 
            tenant ID to connect to
        user : str,                                   
            username as defined in Kalcium
        password : str,
            password for the user in Kalcium
        urlToken : str
            generated token for authentication in Kalcium
        getAliases : bool, optional
            retrieve friendly names as a dictionary for fields and values when instancing Kalcium client.

            It is essential to provide either the `user` and `password` or URL token for login."""
        
        self.baseUrl = baseUrl.rstrip("/")
        self.tenantId = tenantId
        self.mappingAliasesPerTb = None

        if user == "" and urlToken == "":
            raise Exception("Please provide user and pw or url token for login. See docstring for help.")

        # Login to Kalcium
        if type(self.baseUrl) != str or self.tenantId < 1:
            raise Exception("Please provide valid base URL and tenant ID")
        if urlToken:
            self.userObject = self._login_by_url_token(urlToken)
        elif user and password:
            self.userObject = self._login_by_password(user, password)
        else:
            raise Exception("No or incorrect login credentials provided!")

        # Get API
        try:
            self.bearerToken = self.userObject["token"]
        except KeyError as ke:
            raise KeyError("Token could not be retrieved!", ke)

        # Get termbases and languages
        self.systemLanguageIds = self.get_language_ids()
        self.language_map = {value["name"].lower():key for key, value in self.systemLanguageIds.items()}
        self.language_id_map = {value: key for key, value in self.language_map.items()}

        self.availableTermbaseIds = {int(termbase["termbaseId"]) for group in self.userObject["groups"] 
                                     for termbase in group["termbases"] if termbase["isEnabled"]["value"] == True}
        
        if self.availableTermbaseIds != {}:
            self.availableTermbases = self.get_termbases()
            self.availableTermbaseId2NameMap = {tb["id"]: tb["name"] for tb in self.availableTermbases}
            self.availableLanguagesPerTb = self.get_languages_per_tb()
            print(f"Available termbases:\n{self.availableTermbaseId2NameMap}")
            if getAliases:
                #Todo: Create mapping logic for termbase fieldnames and values to 
                # quickly map from hashed values to aliases in JSON responses
                self.mappingAliasesPerTb = self.get_aliases()  # sets self.mappingAliasesPerTb
        
        # Set system-wide parameters:
        self.termbaseIds = [tid for tid in self.availableTermbaseIds]
        self.sourceLanguageIds = [lang for lang in self.availableLanguagesPerTb[self.termbaseIds[0]].keys() if lang != "name"] # Default to first termbase 
        self.targetLanguageIds = [lang for lang in self.availableLanguagesPerTb[self.termbaseIds[0]].keys() if lang != "name"] # Default to first termbase 


    def _login_by_url_token(self, urlToken:str):
        endpoint = self.baseUrl.rstrip("/") + "/kalcrest/authentication/url-token"
        payload = {"tenantId": self.tenantId, "token": urlToken}
        response = requests.post(endpoint, json=payload)
        if response.status_code == 200:
            jsonDict = json.loads(response.text)
            return jsonDict
        else:
            raise Exception(f"Error response returned: {response.status_code}\nError message: {response.text}")

    def _login_by_password(self, user:str, password:str):
        endpoint = self.baseUrl + "/kalcrest/authentication/token"
        payload = {
            "tenantId": self.tenantId,
            "UserName": user,
            "Password": password,
        }
        response = requests.post(endpoint, json=payload)
        if response.status_code == 200:
            jsonDict = json.loads(response.text)
            return jsonDict
        else:
            raise Exception(f"Error response returned: {response.status_code}\nError message: {response.text}")


    def get_aliases(self, termbaseIds: set[int] = set() ):
        endpoint = self.baseUrl + "/kalcrest/lts/terminology/termbases/definition/v1"
        headers = {"Authorization": "Bearer " + self.bearerToken}
        if termbaseIds == []:
            termbaseIds = self.availableTermbaseIds
        for idx, tid in enumerate(termbaseIds):
            if idx < 1:
                endpoint = endpoint + f"?ids={tid}"
            else:
                endpoint = endpoint + f"&ids={tid}"
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            termbaseDefinitions = json.loads(response.text)
            # print(termbaseDefinitions)
            nameAliasDictPerTb = {}
            for termbaseDefinition in termbaseDefinitions:
                termbaseId = termbaseDefinition["termbaseId"]
                nameAliasDictPerTb[termbaseId] = self._recurse_aliases(termbaseDefinition)
            return nameAliasDictPerTb
        else:
            raise Exception(f"Error response returned: {response.status_code}\nError message: {response.text}")
        
    @staticmethod
    def _recurse_aliases(termbaseDefinition: str):
        nameAliasPairs = {}

        # Helper function to recurse
        def recurse(currentParent, currentObject):
            if isinstance(currentObject, dict):
                # If current object is a dictionary
                if currentParent in ["termFieldDefinitionsList", "fieldDefinitionsList"]:
                    try:
                        name = currentObject["name"]
                        alias = currentObject["alias"]
                        if not alias:
                            alias = name
                        nameAliasPairs[name] = alias
                    except KeyError:
                        print("No name or alias found in", currentParent)
                for key, value in currentObject.items():
                    recurse(key, value)  # Recursively process the value
            elif isinstance(currentObject, list):
                # If current object is a list
                for item in currentObject:
                    recurse(currentParent + "List", item)  # Recursively process each item in the list

        recurse("root", termbaseDefinition)  # Start the recursion with the initial dictionary
        return nameAliasPairs

    def get_termbases(self):
        endpoint = self.baseUrl + "/kalcrest/terminology/termbases"
        for idx, tid in enumerate(self.availableTermbaseIds):
            if idx < 1:
                endpoint = endpoint + f"?termbaseIds={tid}"
            else:
                endpoint = endpoint + f"&termbaseIds={tid}"
        headers = {"Authorization": "Bearer " + self.bearerToken}
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            jsonResponse = json.loads(response.text)
            return jsonResponse
        else:
            raise Exception(f"Error response returned: {response.status_code}\nError message: {response.text}")

    def get_language_ids(self):
        endpoint = self.baseUrl + "/kalcrest/terminology/languages"
        headers = {"Authorization": "Bearer " + self.bearerToken}
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            try:
                languages = json.loads(response.text)
                languageIdsDict = {language["id"]: {"name": language["name"], "code": language["code"]} for language in languages}
                return languageIdsDict
            except KeyError as ke:
                raise KeyError("Languages not found in Response!", ke)
        else:
            raise Exception(f"Error response returned: {response.status_code}\nError message: {response.text}")

    def get_languages_per_tb(self):
        languagesPerTb = {}
        for tb in self.availableTermbases:
            languagesPerTb[tb["id"]] = {"name": tb["name"]}
            currentTb = languagesPerTb[tb["id"]]
            for languageId in tb["languageIds"]:
                currentTb[languageId] = self.systemLanguageIds[languageId]
        return languagesPerTb

    def search_in_kalcium(self, term: str, termbaseIds: List[int] = [], sourceLanguageIds: List[int] = [], targetLanguageIds: List[int] = [], searchMode: str = "fuzzy", similarityRate: float = 0.75, filterId: int = -1, useStemmer: bool = False,
        ltsMode: bool = True):
        """
        Search in Kalcium termbase
        """

        # Default to system parameters if no Ids are passed
        termbaseIds = termbaseIds if termbaseIds is not [] else self.termbaseIds
        sourceLanguageIds = sourceLanguageIds if sourceLanguageIds is not [] else self.sourceLanguageIds
        targetLanguageIds = targetLanguageIds if targetLanguageIds is not [] else self.targetLanguageIds
        # Check language
        sourceLanguageIds, targetLanguageIds = self._check_languages(sourceLanguageIds, targetLanguageIds)

        if ltsMode:
            endpoint = self.baseUrl + "/kalcrest/lts/terminology/search/v1"
            queryParams = [
                "term",
                "similarityRate",
                "useStemmer",
                "startIndex",
                "maxCount",
                "sourceLanguageIds",
                "targetLanguageIds",
                "feature",
                "mode",
                "orderingMode",
                "tod",
                "taxonomy",
                "taxonomyNode",
                "useMandatorySearchFilter",
            ]

        else:
            queryParams = []
            endpoint = self.baseUrl + "/kalcrest/terminology/search-raw"
        headers = {"Authorization": "Bearer " + self.bearerToken}
        # Set search mode
        searchModeMap = {"fuzzy": 3, "wildcard": 2, "full-text": 4, "concordance": 7}
        try:
            mode = searchModeMap[searchMode]
        except:
            print("Invalid search mode. Supported search-modes: ", ", ".join(searchModeMap.keys()), "Using 'fuzzy' search instead")
            mode = 3
        

        termbaseSettings = [{"filterId": filterId, "pluginStylesheetId": None, "stylesheetId": -1, "stylesheetIdForPreview": None, "termFilterId": -1, "termbaseId": termbaseId}for termbaseId in termbaseIds]
        payload = {
            "feature": 0,
            "term": term,
            "mode": mode,
            "similarityRate": similarityRate,
            "useStemmer": useStemmer,
            "startIndex": 0,
            "maxCount": 100,
            "sourceLanguageIds": sourceLanguageIds,
            "targetLanguageIds": targetLanguageIds,
            "termbaseSettings": termbaseSettings,
            "termbaseOrderingMode": 1,
            "orderingMode": 1,  # Same as above but for LTS endpoint
            "termbaseOrder": [],
            "tod": [],  # Same as above but for LTS endpoint
            "taxonomy": None,
            "taxonomyNode": None,
            "beginsWith": None,
            "externalId": None,
            "doHighlight": False,
            "collapseResult": False,
            "filterMissingTargetLanguages": False,
            "useMandatorySearchFilter": True,
            "getAdditionalInfo": True,
            "enableLog": True,
        }

        # Transform the payload for the LTS endpoint
        if ltsMode:
            for idx, queryParam in enumerate(queryParams):
                paramValue = payload[queryParam]
                if paramValue is not None:
                    if paramValue:
                        paramValue = "true"
                    elif not paramValue:
                        paramValue = "false"
                else:
                    continue

                if idx < 1:
                    endpoint = endpoint + f"?{queryParam}={paramValue}"
                else:
                    if type(paramValue) == list:
                        for param in paramValue:
                            endpoint = endpoint + f"&{queryParam}={param}"
                    else:
                        endpoint = (endpoint + f"&{queryParam}={escape(str(payload[queryParam]))}")

            print(endpoint)
            response = requests.post(endpoint, headers=headers, json=termbaseSettings)  # only send the termbase settings as payload for LTS
        # Send payload as JSON to search-raw endpoint
        else:
            response = requests.post(endpoint, headers=headers, json=payload)
        # Check response and return
        if response.status_code == 200:
            try:
                jsonResponse = json.loads(response.text)
                return jsonResponse
            except:
                print("Invalid JSON returned!")
        else:
            print("Failed to make search request. Status code:", response.status_code)
            print(response.text)

    def analyze_sentence(self, sentence: str, termbaseIds: List[int] = [], sourceLanguageIds: List[int] = [], targetLanguageIds: List[int] = [], searchMode: str = "fuzzy", similarityRate: float = 0.75, filterId: int = 0, useStemmer: bool = False, includeEntries: bool = True, enableShowNotMatchingCompounds: bool = False):
        """
        Analyze a segment or sentence with Kalcium. Maximum sequence length is 1000 characters.
        :param enableShowNotMatchingCompounds: Include enable show not matching compounds or not.
        :param includeEntries: Include entries or not.
        :param useStemmer: Using a stemmer or not.
        :param filterId: The ID of the filter that is used.
        :param similarityRate: The similarity rate used for searching for the terms.
        :param searchMode: The search mode that is used.
        :param targetLanguageIds: The ID of the target language.
        :param sourceLanguageIds: The ID of the source language.
        :param termbaseIds: The ID of the termbase in which the terms are found.
        :param sentence: The sentence to be analyzed.
        """
        
        # Default to system parameters if no Ids are passed
        termbaseIds = termbaseIds if termbaseIds is not [] else self.termbaseIds
        sourceLanguageIds = sourceLanguageIds if sourceLanguageIds is not [] else self.sourceLanguageIds
        targetLanguageIds = targetLanguageIds if targetLanguageIds is not [] else self.targetLanguageIds
        # Check language
        sourceLanguageIds, targetLanguageIds = self._check_languages(sourceLanguageIds, targetLanguageIds)

        endpoint = self.baseUrl + "/kalcrest/terminology/analyze-sentence"
        headers = {"Authorization": "Bearer " + self.bearerToken}

        # possible search modes
        searchModes = {
            "exact": 1,
            "wildcard": 2,
            "fuzzy": 3,
            "full-text": 4,
            "suffix": 5,
            "prefix": 6,
            "concordance": 7,
        }
        # set search mode
        try:
            mode = searchModes[searchMode]
        except KeyError:
            mode = 3
            print("Invalid search mode. Supported search-modes:", ", ".join(searchModes.keys()), "\nUsing 'fuzzy' search instead")

        termbaseSettings = [{"filterId": filterId, "termFilterId": 0, "stylesheetId": 0, "pluginStylesheetId": 0, "stylesheetIdForPreview": 0, "termbaseId": termbaseId} for termbaseId in termbaseIds]
        payload = {
            "source": sentence,
            "sourceLanguageIds": sourceLanguageIds,
            "targetLanguageIds": targetLanguageIds,
            "mode": mode,
            "similarityRate": similarityRate,
            "useStemmer": useStemmer,
            "matchCase": True,
            "ignoreMatchCaseOnSentenceStart": True,
            "termbaseSettings": termbaseSettings,
            "includeEntries": includeEntries,
            "enableShowNotMatchingCompounds": enableShowNotMatchingCompounds,
            "wordBreakCharacters": ["/"],
        }
        print(endpoint)

        response = requests.post(endpoint, headers=headers, json=payload)
        jsonResponse = {}
        if response.status_code == 200:
            try:
                jsonResponse = json.loads(response.text)
            except Exception as e:
                raise Exception("invalid JSON returned", response.text, e)
        else:
            raise Exception("failed to analyze sentence. status code: ", response.status_code, "\n", response.text)
        return jsonResponse

    #Todo: Move out of Kalcium class
    def get_knowledge(self, text: str, definition_field_name:str, preferred_values:list, allowed_values:list, forbidden_values:list):
        """
        Retrieve additional information from the termbase for the terminology used in the user query
        :param text: The text input containing terms for which additional knowledge is retrieved.
        :return: A nested dictionary that contains additional information about all the terms that occurred in the text and have been found in the termbase
        """

        try:
            search_results = self.analyze_sentence(text, includeEntries=True, searchMode="concordance", similarityRate=0.60, enableShowNotMatchingCompounds=True)
        except Exception as e:
            raise Exception("Error retrieving terms.", text, e,''.join(traceback.format_exception(None, e, e.__traceback__)))
            search_results = {"entries": []}

        # helper to update context (add items to dictionary)
        def update_context(term, language, synonymTerms: list, langDefinition: str, forbiddenTerms: list):
            context[language].append({term: {"definition": langDefinition, "synonyms": synonymTerms, "forbidden synonyms": forbiddenTerms}})

        context = {}
        for entry in search_results["entries"]:
            # get definitions for all languages
            definitions = [field.get("value") for lang in entry["languages"] for field in lang["fields"] if definition_field_name in field.get("name", "")]
            for lang in entry["languages"]:
                langId = lang["languageId"]
                if langId not in context.keys():
                    context[langId] = []
                try:
                    # get definition from language level
                    definition = [field.get("value") for field in lang["fields"] if definition_field_name in field.get("name")][0]
                except (KeyError, IndexError):
                    try:
                        definition = definitions[0]
                    except (KeyError, IndexError):
                        definition = ""
                # get all terms for each usage status
                preferred = [term.get("term") for term in lang["terms"] for field in term.get("fields", []) if any(value in field.get("value", "") for value in preferred_values)]
                admitted = [term.get("term") for term in lang["terms"] for field in term.get("fields", []) if any(value in field.get("value", "") for value in allowed_values)]
                forbidden = [term.get("term") for term in lang["terms"] for field in term.get("fields", []) if any(value in field.get("value", "") for value in forbidden_values)]

                if preferred:
                    mainTerm = preferred[0]
                    synonyms = [term for term in preferred if term != mainTerm]
                    update_context(mainTerm, langId, admitted + synonyms, definition, forbidden)
                # if there are no preferred terms add one admitted term as 'main term' and others as synonyms
                elif admitted:
                    mainTerm = admitted[0]
                    synonyms = [term for term in admitted if term != mainTerm]
                    update_context(mainTerm, langId, synonyms, definition, forbidden)

        return context
    
    # Helpers
    @staticmethod
    def _convert_sup_sub(htmlString: str):
        htmlString = re.sub(r"<sub>(.*?)</sub>", lambda x: x.group(1).translate(str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")), htmlString)
        htmlString = re.sub(r"<sup>(.*?)</sup>", lambda x: x.group(1).translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")), htmlString)
        return htmlString
    
    def _check_languages(self, sourceLanguageIds,targetLanguageIds):
        # check source and target language ids
        try:
            allLanguageIds = set(langId for tb, langs in self.availableLanguagesPerTb.items() for langId in langs.keys())
            allLanguages = {langId: langInfo for tb, langs in self.availableLanguagesPerTb.items() for langId, langInfo in langs.items()}
            for idType, langIds in zip(["search", "target"], [sourceLanguageIds, targetLanguageIds]):
                if not all(lang in allLanguageIds for lang in langIds):
                    invalidLangs = []
                    for idx, lang in enumerate(langIds):
                        if lang not in allLanguageIds:
                            invalidLangs.append(lang)
                            langIds.pop(idx)
                    print(f"Invalid IDs in {idType} languages detected! \nIgnoring the following languages ids: {sorted(set(invalidLangs))}")
            if not sourceLanguageIds:
                raise ValueError(f"Please select at least one valid source language. \nAvailable languages: {json.dumps(allLanguages, indent=2)}")
            elif len(sourceLanguageIds) > 1:
                useStemmer = False
                print("INFO: Stemmer is deactivated due to multiple source languages")
            if not targetLanguageIds:
                print("INFO: Using source language(s) as target language(s).\nAdd valid targetLanguageIds to retrieve different target languages\n")
                targetLanguageIds = sourceLanguageIds
        except Exception as e:
            raise Exception(allLanguageIds, langIds, sourceLanguageIds, targetLanguageIds, e, ''.join(traceback.format_exception(None, e, e.__traceback__)))
        
        return sourceLanguageIds, targetLanguageIds
    
    #-----------------------Retrieval Endpoint-------------------------------
    # Implemented for Kalcium 6.7.2
    def get_entry_content_by_lang_id(self, text:str, profileId:int, sourceLanguageIds:List, targetLanguageIds:List=[]):
        if not text:
            raise Exception("Text cannot be empty")
        text_format = '%20'.join(w for w in quote(text).split())
        endpoint = self.baseUrl + f"/kalcrest/retrieval/content-of-entries-by-langId({profileId})?text=" + text_format + f"&sourceLanguageIds={sourceLanguageIds[0]}"
        if targetLanguageIds:
            target_format = ''.join(f'&targetLanguageIds={id}' for id in targetLanguageIds)
            endpoint = endpoint + target_format

        headers = {"Authorization": "Bearer " + self.bearerToken}
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            entries = json.loads(response.text)
            try:
                content = json.loads(entries["content"])
                return content
            except:
                pass
            return entries["content"]
        else:
            raise Exception(f"Error response returned: {response.status_code}\nError message: {response.text}")