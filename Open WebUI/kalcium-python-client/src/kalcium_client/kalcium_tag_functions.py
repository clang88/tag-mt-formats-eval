def kalcium_tag_format(entry_dictionary, task="translation", format="markdown", add_codeblock=True):
    tag_functions = {"translation": {"markdown": markdown_translation_tag,
                                     "yaml": yaml_translation_tag},
                     "revision" : {"markdown": markdown_revision_tag,
                                   "yaml": yaml_revision_tag}}

    if len(entry_dictionary) < 1:
        context = "No information found in termbase."
    else:
        context = tag_functions[task][format](entry_dictionary)
        
    if add_codeblock:
        context = f"```{format}\n" + context.strip() + "\n```"
    else:
        context = context.strip()

    return context

def markdown_translation_tag(entry_dictionary):
    context = ""
    for entry_id in entry_dictionary.keys():
        concept = entry_dictionary[entry_id]
        context += f"## Concept {entry_id}\n"
        for field in concept["fields"].keys():
            context += f"* {field}: {concept['fields'][field]}\n"  # anschauen
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
    
    return context

def yaml_translation_tag(entry_dictionary):
    context = ""
    for entry_id in entry_dictionary.keys():
        concept = entry_dictionary[entry_id]
        context += f"concept {entry_id}:\n"
        for field in concept["fields"].keys():
            context += f"  - {field}: {concept['fields'][field]}\n"  # anschauen
        for term in concept["terms"].keys():
            # Write source term
            context += f"  - source_term: {term}\n"
            possible_translations = concept["terms"][term]
            #context += f"    - possible translations:\n"
            for idx, translation in enumerate(possible_translations):
                for key in translation:
                    context += f"    - target_term {idx+1}: {key}\n"
                    for field in possible_translations[idx][key].keys():
                        context += f"     - {field}: {possible_translations[idx][key][field]}\n"
        # Add extra new line after each concept
        context += "\n"
    
    return context

# -----------------------------------revision---------------------------
def markdown_revision_tag(entry_dictionary):
    def add_synonyms(context:str, entries:dict, type:str):
        try:
            synonyms = entries[f"{type} terms"]
            context += f"### {type} terms:\n"
            for idx, translation in enumerate(synonyms):
                for term in translation:
                    context += f"{str(idx + 1)}. {term}\n"
                    for field in translation[term]:
                        context += f" * {field}: {translation[term][field]}\n"
        except KeyError:
            pass
        return context

    context = ""

    for entry_id in entry_dictionary.keys():
        concept = entry_dictionary[entry_id]
        context += f"## Concept {entry_id}\n"
        try:
            for field in concept["fields"].keys():
                context += f"* {field}: {concept['fields'][field]}\n"
        except KeyError:
            pass

        for term in concept["terms"].keys():
            context = add_synonyms(context, concept["terms"][term], "preferred")
            context = add_synonyms(context, concept["terms"][term], "allowed")
            context = add_synonyms(context, concept["terms"][term], "forbidden")
        context += "\n"
    return context

def yaml_revision_tag():
    pass