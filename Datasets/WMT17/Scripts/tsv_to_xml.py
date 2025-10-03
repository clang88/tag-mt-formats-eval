from lxml import etree as ET

root = ET.fromstring("<mtf/>")

tsv = open("C:/Users/Christian.Lang/eurocom Translation Service GmbH/AI Box - Dokumente/Testing/Testing_BaseModel/iate.414.terminology.tsv", "r", encoding="utf-8").readlines()

term_pairs = []
for line in tsv:
    cells = line.split("\t")
    for idx in range(2,len(cells),2):
        term_pair = (cells[idx], cells[idx+1])
        term_pairs.append(term_pair)

lang_map = {0:{"name": "English (United Kingdom)",
               "code": "EN-GB"},
            1:{"name": "German (Germany)",
               "code": "DE-DE"}}

for idx,pair in enumerate(set(term_pairs)):
    conceptGrp = ET.SubElement(root,"conceptGrp")
    concept = ET.SubElement(conceptGrp, "concept")
    concept.text = str(idx+1)
    for lang_idx, term_string in enumerate(pair):
        languageGrp = ET.SubElement(conceptGrp,"languageGrp")
        language = ET.SubElement(languageGrp,"language", type=lang_map[lang_idx]["name"],lang=lang_map[lang_idx]["code"])
        termGrp = ET.SubElement(languageGrp,"termGrp")
        term = ET.SubElement(termGrp,"term")
        term.text = term_string

output_dir = "C:/Users/Christian.Lang/eurocom Translation Service GmbH/AI Box - Dokumente/Testing/Testing_BaseModel/scripts"
with open(f"{output_dir}/iate.414.terminology.xml", "wb") as out:
    out.write(ET.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=True))

print(f"Conversion saved to {output_dir}")