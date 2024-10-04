import imp
import xml.etree.ElementTree as ET
import random
import json
import wikitextparser as wtp
import re


class XMLParser:
    def __init__(self, xml_file_path, namespaces=None):
        self.namespaces = namespaces or {'mw': 'http://www.mediawiki.org/xml/export-0.11/'}
        self.root = self.get_xml_root(xml_file_path)
        self.total_pages = 0
        self.failed_quests = []
        self.quests_without_infobox = []  # List to hold quests without Memory Infobox

    def get_xml_root(self, xml_file_path):
        try:
            tree = ET.parse(xml_file_path)
            return tree.getroot()
        except ET.ParseError as e:
            print(f"Error parsing XML file: {e}")
            return None

    def count_unique_keys(self, quests):
        unique_keys = set()
        for quest in quests:
            unique_keys.update(quest.keys())
        return len(unique_keys)

    def get_unique_keys(self, quests):
        unique_keys = set()
        for quest in quests:
            unique_keys.update(quest.keys())
        return unique_keys

    def sanitize_text(self, text):
        # Implement or use your existing sanitize_text method
        if text:
            return text.replace("\r", "").replace("\n", "").strip()
        return text

    def sanitize_tag_name(self, tag_name):
        # Implement or use your existing sanitize_tag_name method
        sanitized_name = re.sub(r'\W+', '_', tag_name)
        if not sanitized_name[0].isalpha():
            sanitized_name = "Tag_" + sanitized_name
        return sanitized_name

    def parse_all_pages(self, limit=None, random_selection=False):
        all_quests = []
        pages = list(self.root.findall('.//mw:page', namespaces=self.namespaces))

        if random_selection and limit:
            pages = random.sample(pages, min(limit, len(pages)))

        for page in pages[:limit]:
            self.total_pages += 1
            quest = self.parse_page(page)
            if quest:
                all_quests.append(quest)

        # Generate typo dict and fix typos in keys
        all_keys = set().union(*(d.keys() for d in all_quests))
        typo_dict = self.generate_typo_dict_keys(all_keys)
        all_quests = self.fix_typos_in_keys(all_quests, typo_dict)

        return all_quests

    def save_to_json(self, data, file_path):
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def parse_page(self, page):
        try:
            quest = {}
            title = page.find('mw:title', namespaces=self.namespaces)
            id = page.find('mw:id', namespaces=self.namespaces)

            if title is not None and title.text is not None:
                quest['Quest_Name'] = title.text.strip()
            else:
                quest['Quest_Name'] = "Unknown"

            if id is not None and id.text is not None:
                quest['Quest_ID'] = id.text.strip()
            else:
                quest['Quest_ID'] = "Unknown"

            revision = page.find('mw:revision', namespaces=self.namespaces)
            if revision:
                quest['Revision'] = self.parse_revision(revision)

            text = revision.find('mw:text', namespaces=self.namespaces) if revision else None
            if text is not None and text.text is not None:
                self.parse_text(text.text, quest)
                # Check if Memory Infobox is found
                if 'MemoryInfobox' not in quest or not quest['MemoryInfobox']:
                    self.quests_without_infobox.append(quest)

            return quest
        except Exception as e:
            quest_name = quest.get('QuestName', "Unknown")
            self.failed_quests.append(quest_name)
            print(f"Failed to parse quest: {quest_name}, Error: {e}")
            return None

    def parse_revision(self, revision):
        revision_data = {}
        for elem in revision:
            if elem.text:
                revision_data[elem.tag.split('}')[-1]] = elem.text.strip()
        return revision_data

    def parse_text(self, text_content, quest):
        parsed = wtp.parse(text_content)

        # Find the start index of the first section
        first_section_start = text_content.find('==')
        if first_section_start == -1:
            first_section_start = len(text_content)

        # Extract Tags from the beginning of the text up to the first section
        tags_text = text_content[:first_section_start].strip()
        self.parse_tags(tags_text, quest, 'Tags')

        # Search for 'Memory Infobox' or 'Memory_Infobox' in a case-insensitive manner
        infoboxes = [template for template in parsed.templates if
                     template.name.strip().lower().replace('_', ' ') == 'memory infobox']
        memory_infobox_data = {}
        infobox_end_index = 0

        if infoboxes:
            infobox = infoboxes[0]
            for param in infobox.arguments:
                if param.name and param.value:
                    memory_infobox_data[param.name.strip()] = param.value.strip()
            quest['MemoryInfobox'] = memory_infobox_data
            infobox_end_index = text_content.find(str(infobox)) + len(str(infobox))

        # Extract General Description
        general_description = text_content[infobox_end_index:first_section_start].strip()
        quest['General_Description'] = general_description

        
        
        # Extract Sections
        for section in parsed.sections:
            if section.title:
                section_title = section.title.strip().replace(' ', '_')
                if section_title:
                    quest[f'Section_{section_title}'] = section.contents.strip()

    def parse_tags(self, text_content, quest, tag_category):
        tags = re.findall(r'{{(.*?)}}', text_content, re.DOTALL)
        quest[tag_category] = {}
        for tag in tags:
            tag_parts = tag.split('|')
            tag_name = self.sanitize_tag_name(tag_parts[0])

            # Check if the tag is Memory Infobox, considering variations in naming
            if 'memory_infobox' in tag_name.lower().replace(' ', '_'):
                continue

            tag_content = self.sanitize_text(' | '.join(tag_parts[1:]))
            quest[tag_category][f'Tag_{tag_name}'] = {"description": tag_content}

    def generate_typo_dict_keys(self, all_keys):
        # Here you can write logic to automatically generate typo_dict based on all_keys
        # Or you can manually create this dict
        typo_dict = {
            'Section_Behind_the_Scenes': 'Section_Behind_the_scenes',
            'Section_Behind_the_scenes_': 'Section_Behind_the_scenes',
            'Section_Behind_the_scnes': 'Section_Behind_the_scenes',
            'Section_Description_': 'Section_Description',
            'Section_Dialogue_': 'Section_Dialogue',
            'Section__Behind_the_scenes_': 'Section_Behind_the_scenes',
            'Section__Description': 'Section_Description',
            'Section__Dialogue': 'Section_Dialogue',
            'Section__Gallery': 'Section_Gallery',
            'Section__Gallery_': 'Section_Gallery',
            'Section__Outcome': 'Section_Outcome',
            'Section__Outcome_': 'Section_Outcome',
            'Section__References': 'Section_References',
            'Section__References_': 'Section_References',
            'Section_Reference': 'Section_References',
            'Section_Trivia': 'Section_Trivia',
            'Section__Trivia_': 'Section_Trivia',
            'Section_Message': 'Section_Messages',
            'Section_Outcome_': 'Section_Outcome',
        }
        return typo_dict

    def fix_typos_in_keys(self, json_data, typo_dict):
        corrected_data = []
        for quest in json_data:
            corrected_quest = {}
            for key, value in quest.items():
                corrected_key = typo_dict.get(key,
                                              key)  # Get the corrected key if exists, otherwise use the original key
                corrected_quest[corrected_key] = value
            corrected_data.append(corrected_quest)
        return corrected_data

    def save_quests_without_infobox(self, file_path):
        with open(file_path, 'w') as f:
            json.dump(self.quests_without_infobox, f, indent=4)
            
    def count_key_occurrences(self, quests):
        key_counts = {} # Dict to hold key counts
        for quest in quests:
            for key in quest.keys():
                if key not in key_counts:
                    key_counts[key] = 0
                key_counts[key] += 1
        return key_counts
    
    def print_unique_keys_info(self):
        unique_keys = set()
        for quest in self.quests_without_infobox:
            unique_keys.update(quest.keys())
        print(f"Unique keys in quests without infobox: {len(unique_keys)}")
        print(f"Keys: {', '.join(unique_keys)}")
        
xml_file_path = "Datasets/MainDatabaseNew.xml"

# Example usage
xml_parser = XMLParser(xml_file_path)
quests = xml_parser.parse_all_pages(limit=2, random_selection=True)
all_quests = xml_parser.parse_all_pages()
key_counts = xml_parser.count_key_occurrences(all_quests)


# Example usage
xml_parser.print_unique_keys_info()
xml_parser.save_to_json(all_quests, "Memories relived using the Animus HR-8.5.json")
print(xml_parser.count_unique_keys(all_quests))
print(xml_parser.get_unique_keys(all_quests))
print(f"Total quests: {xml_parser.total_pages}")
xml_parser.save_quests_without_infobox("quests_without_infobox.json")
print(f"Quests without infobox: {len(xml_parser.quests_without_infobox)}")


for key, count in key_counts.items():
    print(f"{key}: {count}")
    
files_without_questname = []
for quest in all_quests:
    if 'QuestName' not in quest:
        files_without_questname.append(quest)

print(f"Number of files without QuestName: {len(files_without_questname)}")

print(f"Number of failed quests: {len(xml_parser.failed_quests)}")