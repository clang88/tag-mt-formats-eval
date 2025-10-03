from typing import List
from kalcium_client.client import Kalcium

class Translator(Kalcium):
    def __init__(self, kalciumLoginDetails: dict = None, get_aliases: bool = False):
        super().__init__(kalciumLoginDetails, get_aliases)

    @staticmethod
    def get_field_info(start_level, field_name: str, level: str, primaryLanguageIds: List[int] = None, secondaryLanguageIds: List[int] = None) -> str:
        if primaryLanguageIds is None:
            primaryLanguageIds = []
        if secondaryLanguageIds is None:
            secondaryLanguageIds = []

        field_info = ""

        if level == "language":
            language_fields = {}
            fallbackLanguageId = 815
            all_languages = (primaryLanguageIds + secondaryLanguageIds + [fallbackLanguageId])
            for field_item in start_level["languages"]:
                languageId = field_item["languageId"]
                for field in field_item["fields"]:
                    if field_name in field["name"].lower():
                        language_fields[languageId] = field["value"]
            for languageId in all_languages:
                try:
                    field_info = language_fields[languageId]
                    break
                except KeyError:
                    continue
        elif level == "term":
            for field_item in start_level["fields"]:
                if field_name in field_item["name"].lower():
                    field_info = field_item["value"]

        return field_info

    def find_translations(self, text: str, sourceLanguageIds: List[int] = None, targetLanguageIds: List[int] = None):
        """
        Analyze the source text and get the correct translation for the terminology in the text.
        :param targetLanguageIds: The ID of the target language.
        :param sourceLanguageIds: The ID of the source langauge.
        :param text: Source text to be analyzed.
        :return: The found term pairs
        """

        # Default to system parameters if no Ids are passed
        sourceLanguageIds = (sourceLanguageIds if sourceLanguageIds is not None else self.sourceLanguageIds)
        targetLanguageIds = (targetLanguageIds if targetLanguageIds is not None else self.targetLanguageIds)

        try:
            search_results = self.analyze_sentence(text, includeEntries=True, similarityRate=0.70, searchMode="fuzzy", enableShowNotMatchingCompounds=False, useStemmer=True)
        except Exception as e:
            print("Error retrieving terms.", e)
            raise Exception(str(e) + text)
        if search_results:
            hits = {}
            for hit in search_results["hits"]:
                entryId = hit["entryId"]["id"]
                term = hit["term"]
                if entryId not in hits.keys():
                    hits[entryId] = []
                if term not in hits[entryId]:
                    hits[entryId].append(term)
            # only keep exact matches, if available
            for entry_id in hits.keys():
                exact_matches = [hit for hit in hits[entry_id] if hit in text]
                if exact_matches:
                    hits[entry_id] = exact_matches

            # Create translation dictionary
            translation_dict = {}
            for entry in search_results["entries"]:
                curr_entryId = entry["id"]["id"]
                target_language = [language for language in entry["languages"] if language["languageId"] in targetLanguageIds]
                if not target_language:
                    continue
                # Get Definitions for entry
                definition = Translator.get_field_info(entry, "definition", "language", targetLanguageIds, sourceLanguageIds)
                # Add info to entry dictionary
                if curr_entryId not in translation_dict.keys():
                    translation_dict[curr_entryId] = {"terms": {}, "fields": {}}
                if definition:
                    translation_dict[curr_entryId]["fields"] = {"definition": definition}
                for term in hits[curr_entryId]:
                    source_term = term
                    translation_dict[curr_entryId]["terms"][source_term] = []
                    current_term = translation_dict[curr_entryId]["terms"][source_term]
                    target_terms = []
                    for term in target_language[0]["terms"]:
                        target_term = term["term"]
                        deprecated = False
                        for field in term.get("fields", []):
                            if "usageStatus" in field.get("name", "") and "deprecated" in field.get("value", ""):
                                deprecated = True
                                break
                        if deprecated:
                            break
                        # Get usage_note
                        usage_note = Translator.get_field_info(term, "note", "term", targetLanguageIds, sourceLanguageIds)
                        target_dict = {target_term: {}}
                        if usage_note:
                            target_dict[target_term]["usageNote"] = usage_note
                        current_term.append(target_dict)
                        target_terms.append(target_term)
                    # Remove empty concepts
                if not target_terms:
                    del translation_dict[curr_entryId]

            context = ""
            for entry_id in translation_dict.keys():
                concept = translation_dict[entry_id]
                context += f"## Concept {entry_id}\n"
                for field in concept["fields"].keys():
                    context += f"* {field}: {concept['fields'][field]}\n"
                for term in concept["terms"].keys():
                    # Write source term
                    context += f"### {term}\n"
                    possible_translations = concept["terms"][term]
                    context += f"#### Possible translations:\n"
                    for idx, translation in enumerate(possible_translations):
                        for key in translation:
                            context += f"{str(idx + 1)}. {key}\n"
                            for field in possible_translations[idx][key].keys():
                                context += f"\t{field}: {possible_translations[idx][key][field]}\n"
                # Add extra new line after each concept
                context += "\n"
            if not context:
                context = "No information found in the termbase."
            context = "```markdown\n" + context.strip() + "\n```"
            return str(context)
        else:
            return "```markdown\nNo information found in the termbase.\n```"