from kalcium_client.client import KalciumClient
from typing import List
import json

class Termchecker(KalciumClient):
    def __init__(self, kalciumLoginDetails: dict = {}, get_aliases: bool = False):
        super().__init__(kalciumLoginDetails, get_aliases)

    def check_terminology(self, text: str, sourceLanguageIds: List[int] = []) -> str:
        """
        Retrieve terminology from the termbase, by recognizing terminology in the full query of the user.
        :param text: The user query.
        :return: Context of the found terms as a markdown bullet list.
        """

        # Default to system parameters if no Ids are passed
        sourceLanguageIds = (sourceLanguageIds if sourceLanguageIds is not None else self.sourceLanguageIds)

        search_results = self.analyze_sentence(text, includeEntries=True, searchMode="concordance", similarityRate=0.70, useStemmer=True, enableShowNotMatchingCompounds=False)
        if search_results:
            hits = {}
            for hit in search_results["hits"]:
                entryId = hit["entryId"]["id"]
                term = hit["term"]
                if entryId not in hits.keys():
                    hits[entryId] = []
                if term not in hits[entryId]:
                    hits[entryId].append(term)
            term_hits = [term for hit in hits.values() for term in hit]

            context = self.get_knowledge(text)
            correction_dict = {}
            for languageId in sourceLanguageIds:
                if languageId in context.keys():
                    idx = 1
                    for concept in context[languageId]:
                        correction_dict[f"concept{str(idx)}"] = {}
                        for preferred_term in concept.keys():
                            current_entry = concept[preferred_term]
                            forbidden_terms = [term for term in current_entry.get("forbidden synonyms", []) if term in term_hits]
                            definition = str(current_entry.get("definition", ""))
                            correction_dict[f"concept{str(idx)}"]["Forbidden terms"] = {}
                            for forbidden_term in forbidden_terms:
                                correction_dict[f"concept{str(idx)}"]["Forbidden terms"] = {forbidden_term: preferred_term}
                        if not correction_dict[f"concept{str(idx)}"]["Forbidden terms"]:
                            del correction_dict[f"concept{str(idx)}"]
                        elif definition:
                            correction_dict[f"concept{str(idx)}"]["Definition"] = str(definition)
                            idx += 1
                        else:
                            idx += 1
            context_string = json.dumps(correction_dict, ensure_ascii=False, indent=2)
        else:
            return "No forbidden terms found."
        return context_string