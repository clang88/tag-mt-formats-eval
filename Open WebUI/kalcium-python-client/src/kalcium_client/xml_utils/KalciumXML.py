import logging
from lxml import etree as ET
import re
import uuid
import chardet
from collections import Counter
from xml.sax.saxutils import escape, unescape


class KalciumXML:
    # Parse the schema
    field_xml_schema_root = ET.XML(open("./Kalcium-v3-fields.xsd", "rb").read())
    field_xml_schema = ET.XMLSchema(field_xml_schema_root)
    term_xml_schema_root = ET.XML(open("./Kalcium-v3-terms.xsd", "rb").read())
    term_xml_schema = ET.XMLSchema(term_xml_schema_root)
    def __init__(self):
        pass

    def from_dict(self, entry_dictionary: dict, generate_entry_ID=True, start_ID: int = 0, generate_uuid=False):
        root = ET.fromstring("<kalciumEntries/>")

        all_langs = {lang for key in entry_dictionary.keys() for lang in entry_dictionary[key]["languages"]}

        languages = [(str(idx + 1), l) for idx, l in enumerate(all_langs)]
        languageDefinitions = ET.SubElement(root, "languageDefinitions")
        language_dict = {}
        for language in languages:
            language_dict[language[1]] = {"id": language[0],
                                          "n": language[1].split("|")[0],
                                          "c": language[1].split("|")[1]}
            l = ET.SubElement(languageDefinitions, "l")
            for key in language_dict[language[1]]:
                l.attrib[key] = language_dict[language[1]][key]

        term_count = 0
        for idx, key in enumerate(entry_dictionary.keys()):
            # generate entry_element
            entry_ele = ET.SubElement(root, "e", ec="Unspecified", ver="3")
            entry = entry_dictionary[key]
            # Create id element
            if generate_entry_ID or ("entry_ID" not in entry_dictionary[key].keys()):
                entry_ID = str(start_ID + idx + 1)
            else:
                entry_ID = entry_dictionary[key]["entry_ID"]
            if generate_uuid:
                uuid_str = str(uuid.uuid4())
            else:
                uuid_str = key
            id_ele = ET.SubElement(entry_ele, "id", id=entry_ID, uuid=uuid_str)
            # Add entry level fields
            fields = entry.get("fields",[])
            entry_fields = self.add_fields(entry_ele, fields)
            # Add languages
            for language in entry["languages"].keys():
                language_ele = ET.SubElement(entry_ele, "l", lid=language_dict[language]["id"])
                # Add language-level fields
                fields = entry["languages"][language].get("fields",[])
                language_fields = self.add_fields(language_ele, fields)
                terms = entry["languages"][language]["terms"]
                for term in terms:
                    term_uuid = str(uuid.uuid4())
                    term_ele = ET.SubElement(language_ele, "t",
                                             head="false",
                                             id="1" + "/" + entry_ID + "/" + term_uuid,
                                             xid=term_uuid)
                    try:
                        term_ele.attrib["t"] = self.ensure_valid_xml(term["term"], self.term_xml_schema)
                    except TypeError as err:
                        logging.error(err)
                        logging.error(term)
                    # Add term-level fields
                    fields = term.get("fields",[])
                    term_fields = self.add_fields(term_ele, fields)

        return root, entry_ID

    def add_fields(self, parent, fields, field_elements:list = []):
        if len(fields) != 0:
            for field, values in fields.items():
                if type(values) == str:
                    value_string = values
                elif type(values) == list:
                    value_string = "|".join(values)
                elif type(values) == dict:
                    nested_values = values["values"]
                    if type(nested_values) == str:
                        value_string = nested_values
                    elif type(nested_values) == list:
                        value_string = "|".join(values["values"])
                field_ele = self.create_field(parent, field, value_string)
                field_elements.append(field_ele)
                # Add subfields, if available
                if type(values) == dict:
                    field_elements = self.add_fields(field_ele, values["fields"], field_elements)

            return field_elements
        else:
            return []

    def readXML(self, XML_path: str, return_fields=True):
        termbase = ET.parse(XML_path)
        field_dict = {}
        if return_fields:
            field_dict["entry"] = sorted({field.attrib["n"] for field in \
                                          termbase.xpath("//f[not(ancestor::l)]")})
            field_dict["language"] = sorted({field.attrib["type"] for field in \
                                             termbase.xpath("//f[ancestor::l and not(ancestor::t)]")})
            field_dict["term"] = sorted({field.attrib["type"] for field in \
                                         termbase.xpath("//t//f")})
        return termbase, field_dict

    def create_field(self, parent, name: str, value: str):
        # Check if value is valid Kalcium XML
        valid_value = self.ensure_valid_xml(value, self.field_xml_schema)
        if valid_value != value:
            logging.info(f"Converted {value} to {valid_value}")
        try:
            field = ET.SubElement(parent, "f", n=name, v=valid_value)
            return field
        except Exception as err:
            logging.error(f"Critical error when trying to create field {name}: {valid_value}. Aborting script.")
            raise

    def ensure_valid_xml(self, text: str, xml_schema): # Currently only checks if Field is valid, should be expanded to check full Kalcium XML
        """This checks the validity a Kalcium-XML using the passed XML-Schema.
        It first checks the strings for < or &, if none are present, it returns the string as is.
        If the string contains any of < or &, it will first check if the XML and
        validates against the schema after escaping and then unescaping.
        If not, we try to replace &amp; with &amp;amp; in the escaped version and unescape again.
        Finally, all major XML (&, <, >) entitities are fully double-escaped to make sure it is valid.
        This may result in a loss of formatting"""
        if "<" not in text and "&" not in text:
            return text
        else:
            unmodified_text = text
            try:
                try:
                    text = unescape(escape(text))
                    xml_doc = ET.XML("<f>" + text + "</f>")
                except ET.XMLSyntaxError:
                    logging.warning(f"Invalid XML provided: '{text}'")
                    logging.info(f"Attempting to fix by double-escaping &.")
                    text = unescape(escape(text).replace("&amp;", "&amp;amp;"))
                    xml_doc = ET.XML("<f>" + text + "</f>")
                # Validate the XML
                xml_schema.assertValid(xml_doc)
                logging.info(f"XML successfully validated as:'{text}'")
                return text
            except (ET.XMLSyntaxError, ET.DocumentInvalid) as err:
                text = escape(unmodified_text)
                logging.warning(err)
                logging.warning(f"XML fully escaped (potential loss of formatting) to: '{text}'")
                return text

    def create_crossreference(self, parent, language, term, text):
        pass

    def create_system_details(self, parent, user: str, date: str, transac_type: str):
        pass