from calendar import c
from itertools import count
import json
from enum import Enum
import re
import struct
from fuzzywuzzy import fuzz

from regex import P
from DialogueDataStructurer import DialogueDataStructurer
import os
import csv
import logging

class DataManipulator:
    def __init__(self, json_file_path=None):
        self.data = self.load_json(json_file_path) if json_file_path else []
        self.dialogue_structurer = DialogueDataStructurer(self.data)
        
    def load_json(self, json_file_path):
        # Load data from a JSON file
        with open(json_file_path, 'r', encoding="utf-8") as f:
            return json.load(f)

    def save_json(self, json_file_path):
        # Save data to a JSON file with null values removed at the first level
        cleaned_data = []
        for quest in self.data:
            cleaned_quest = {k: v for k, v in quest.items() if v is not None}
            cleaned_data.append(cleaned_quest)

        with open(json_file_path, 'w', encoding="utf-8") as f:
            json.dump(cleaned_data, f, indent=4)

    def get_quest_by_index(self, index):
        # Retrieve a quest by its index
        return self.data[index] if 0 <= index < len(self.data) else None
    
    def get_quests_by_index_range(self, start, end):
        if 0 <= start < len(self.data) and 0 < end <= len(self.data):
            return self.data[start:end]
        else:
            return None

    def get_length(self):
        
        # Get the number of quests in the dataset
        return len(self.data)
    
    def sanitize_filename(self, name):
        
        """
        Sanitize the quest name to be used as a valid file name.
        :param name: The original quest name.
        :return: A sanitized, valid file name.
        """
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for ch in invalid_chars:
            name = name.replace(ch, '_')
        return name
    
    def get_dialogue_by_name(self, name):
        # Retrieve dialogue for a quest by its name
        for quest in self.data:
            if quest.get('Quest_Name') == name:
                return quest.get('Section_Dialogue')
        return None

    def get_generic_value(self, index, key):
        """
        Retrieve a specific value from the generic level of a quest.
        """
        try:
            quest = self.data[index]
            return quest.get(key, "Key not found")
        except IndexError:
            return "Invalid index"

    def get_quests_by_appearance(self, appearance):
        """
        Get quests by appearance value.
        :param appearance: The appearance value to match.
        :return: List of quests with the specified appearance.
        """
        matching_quests = []
        for quest in self.data:
            memory_infobox = quest.get('MemoryInfobox', {})
            if memory_infobox.get('appearance') == appearance:
                matching_quests.append(quest)
        return matching_quests

    def add_feature_to_quest(self, index, key, value):
        """
        Add a new feature (key-value pair) to a quest at a generic level.
        """
        try:
            self.data[index][key] = value
        except IndexError:
            return "Invalid index"

    def add_feature_to_section(self, index, section, key, value):
        """
        Add a new feature (key-value pair) to a specific section of a quest.
        """
        try:
            self.data[index][section][key] = value
        except (IndexError, KeyError):
            return "Invalid index or section"
        
    def find_missing_structured_dialogues(self):
        """
        Identify quests that have 'Section_Dialogue' but no 'Structured_Dialogue'.
        Returns a list of such quests.
        """
        missing_structured_dialogues = []
        for quest in self.data:
            if 'Section_Dialogue' in quest and 'Structured_Dialogue' not in quest:
                missing_structured_dialogues.append(quest)
        return missing_structured_dialogues

    def save_missing_structured_dialogues(self, output_file_path):
        """
        Save quests that have 'Section_Dialogue' but no 'Structured_Dialogue' to a JSON file.
        :param output_file_path: Path for the output JSON file.
        """
        missing_dialogues = self.find_missing_structured_dialogues()
        with open(output_file_path, 'w', encoding='utf-8') as file:
            json.dump(missing_dialogues, file, indent=4)
        print(f"Saved {len(missing_dialogues)} quests with missing structured dialogues to {output_file_path}")

    def get_all_quests(self):
        return self.get_quests_by_range(0, len(self.data))

    def get_memory_infobox_by_index(self, index):
        return self.get_generic_value(index, 'MemoryInfobox')

    def get_dialogue_by_index(self, index):
        return self.get_generic_value(index, 'Section_Dialogue')

    def get_general_description_by_index(self, index):
        return self.get_generic_value(index, 'GeneralDescription')

    def get_quest_name_by_index(self, index):
        return self.get_generic_value(index, 'Quest_Name')

    def get_tags_by_index(self, index):
        return self.get_generic_value(index, 'Tags')

    def get_revision_by_index(self, index):
        return self.get_generic_value(index, 'Revision')

    def get_quest_by_name(self, name):
        if not isinstance(name, str):
            raise ValueError("Quest name must be a string")
        for quest in self.data:
            if 'Quest_Name' in quest and quest['Quest_Name'] == name:
                return quest
        return None
    
    def save_quests_by_index(self, start, end, output_file_path):
        """
        Save quests by index range to a JSON file.
        :param start: Start index.
        :param end: End index.
        :param output_file_path: Path to the output JSON file.
        """
        quests = self.get_quests_by_index_range(start, end)
        with open(output_file_path, 'w', encoding="utf-8") as f:
            json.dump(quests, f, indent=4)
    
    def get_structured_dialogue_by_index(self, index):
        """
        Retrieve structured dialogue for a quest by its index.
        :param index: Index of the quest.
        :return: Structured dialogue of the quest or None if quest is not found.
        """
        quest = self.get_quest_by_index(index)
        dialogue_structurer = DialogueDataStructurer(self.data)
        if quest:
            dialogue_text = quest.get('Section_Dialogue', '')
            return dialogue_structurer.process_dialogue(quest['Quest_Name'], dialogue_text)
        else:
            print(f"Quest with index '{index}' not found.")
            return None

    def get_memory_infobox_statistics(self):
        """
        Count unique occurrences of MemoryInfobox parameters except those with values longer than 40 characters.
        :return: Dictionary with counts of unique values for each parameter.
        """
        infobox_stats = {}
        for quest in self.data:
            memory_infobox = quest.get('MemoryInfobox', {})
            for key, value in memory_infobox.items():
                if len(str(value)) <= 40:  # Ignore long values
                    if key not in infobox_stats:
                        infobox_stats[key] = set()  # Use a set to keep track of unique values
                    infobox_stats[key].add(value)

        # Convert sets to counts
        for key in infobox_stats:
            infobox_stats[key] = len(infobox_stats[key])

        return infobox_stats

    def get_quests_by_appearance_and_source(self, appearance, source):
        """
        Get quests with specific appearance and source values in their MemoryInfobox.
        :param appearance: The appearance value to match.
        :param source: The source value to match.
        :return: List of quests with the specified appearance and source.
        """
        matching_quests = []
        for quest in self.data:
            memory_infobox = quest.get('MemoryInfobox', {})
            if memory_infobox.get('appearance') == appearance and memory_infobox.get('source') == source:
                matching_quests.append(quest)
        return matching_quests

    def get_unique_source_appearance_pairs(self):
        """
        Count occurrences of unique (source, appearance) pairs in MemoryInfobox.
        :return: Dictionary with counts of each unique pair.
        """
        pair_counts = {}
        for quest in self.data:
            memory_infobox = quest.get('MemoryInfobox', {})
            source = memory_infobox.get('source')
            appearance = memory_infobox.get('appearance')
            if source and appearance:
                pair = (source, appearance)
                if pair in pair_counts:
                    pair_counts[pair] += 1
                else:
                    pair_counts[pair] = 1

        stats = {
            'Number of unique (source, appearance) pairs': len(pair_counts),
            'Total number of pairs': sum(pair_counts.values()),
            'Average number of quests per pair': sum(pair_counts.values()) / len(pair_counts),
            'Max number of quests per pair': max(pair_counts.values()),
            'Min number of quests per pair': min(pair_counts.values()),
            'Pairs with max number of quests': [(pair, count) for pair, count in pair_counts.items() if count == max(pair_counts.values())],
            'Pairs with min number of quests': [(pair, count) for pair, count in pair_counts.items() if count == min(pair_counts.values())]
            
        }

        print(stats)
        print("===========================================")
        return pair_counts

    def get_quests_by_memory_infobox_value(self, key, value):
        """
        Get quests that contain a specific value for a given key in their MemoryInfobox.
        :param key: The key to search for in the MemoryInfobox.
        :param value: The value to match.
        :return: List of quests with the specified value for the key.
        """
        matching_quests = []
        for quest in self.data:
            memory_infobox = quest.get('MemoryInfobox', {})
            if memory_infobox.get(key) == value:
                matching_quests.append(quest)
        print(f"Number of quests with value '{value}' for key '{key}': {len(matching_quests)}")
        return matching_quests

    def save_quests_by_memory_infobox_values(self, key, values, output_file_path):
        """
        Save quests that contain specific values for a given key in their MemoryInfobox to a JSON file.
        :param key: The key to search for in the MemoryInfobox.
        :param values: List of values to match.
        :param output_file_path: Path to the output JSON file.
        """
        matching_quests = []
        for quest in self.data:
            memory_infobox = quest.get('MemoryInfobox', {})
            if memory_infobox.get(key) in values:
                matching_quests.append(quest)

        with open(output_file_path, 'w', encoding="utf-8") as f:
            json.dump(matching_quests, f, indent=4)
    
    def get_unique_values_for_memory_infobox_key(self, key):
        """
        Get all unique values for a specific key in the MemoryInfobox across all quests.
        :param key: The key to search for in the MemoryInfobox.
        :return: Set of unique values for the key.
        """
        pair_counts = {}
        for quest in self.data:
            memory_infobox = quest.get('MemoryInfobox', {})
            key_value = memory_infobox.get(key)
            if key in memory_infobox:
                pair_counts[key_value] = pair_counts.get(key_value, 0) + 1      
            else:
                pair_counts[key_value] = 1
                
        stats = {
            'Number of unique () pairs': len(pair_counts),
            'Total number of pairs': sum(pair_counts.values()),
            'Average number of quests per pair': sum(pair_counts.values()) / len(pair_counts),
            'Max number of quests per pair': max(pair_counts.values()),
            'Min number of quests per pair': min(pair_counts.values()),
            'Pairs with max number of quests': [(pair, count) for pair, count in pair_counts.items() if count == max(pair_counts.values())],
            'Pairs with min number of quests': [(pair, count) for pair, count in pair_counts.items() if count == min(pair_counts.values())]
            
        }
        print(stats)
        return pair_counts
    
    def delete_revision_text(self):
        for quest in self.data:
            if 'Revision' in quest:
                quest['Revision'].pop('text', None)

    def replace_essentially_null_with_none(self):
        """
        Replace essentially null values (like empty strings) with None.
        This method iterates through each quest and its nested elements.
        """
        for quest in self.data:
            for key, value in quest.items():
                if self.is_essentially_null(value):
                    quest[key] = None
                elif isinstance(value, dict):  # If the value is a dictionary, check its fields
                    for subkey, subvalue in value.items():
                        if self.is_essentially_null(subvalue):
                            value[subkey] = None

    @staticmethod
    def is_essentially_null(value):
        """
        Check if a value is essentially null (empty string or similar).
        """
        return value == "" or value == "''" or value == '""' or value is None

    def sanitize_memory_infobox(self):
        """Sanitize the MemoryInfobox fields in each quest."""
        for quest in self.data:
            memory_infobox = quest.get('MemoryInfobox', {})
            for key, value in memory_infobox.items():
                sanitized_value = self.sanitize_value(value)
                memory_infobox[key] = sanitized_value
                
    def save_dialogues_to_csv1(self, output_csv_file):
        """
        Save all structured dialogues to a CSV file.
        :param output_csv_file: The path to the output CSV file.
        """
        with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = None
            for quest in self.data:
                quest_name = quest.get('Quest_Name', 'UnknownQuest')
                structured_dialogue = quest.get('Structured_Dialogue', [])

                for dialogue_element in structured_dialogue:
                    dialogue_element['Quest_Name'] = quest_name  # Add QuestName to each dialogue element
                    # Add additional fields to dialogue_element
                    memory_infobox = quest.get('MemoryInfobox', {})
                    dialogue_element['Chapter_Name'] = quest.get('Chapter_Name', '')
                    dialogue_element['Chapter_Type'] = quest.get('Chapter_Type', '')
                    dialogue_element['Quest_SequenceID'] = quest.get('Quest_SequenceID', '')
                    dialogue_element['Chapter_SequenceID'] = quest.get('Chapter_SequenceID', '')
                    dialogue_element['Quest_Location'] = memory_infobox.get('location', '')
                    dialogue_element['Quest_Date'] = memory_infobox.get('date', '')
                    dialogue_element['Speaker'] = ''
                    dialogue_element['Dialogue'] = ''


                    # Separate speaker and dialogue
                    if dialogue_element.get('segment_type') == 'Dialogue':  # Corrected line
                        speaker, dialogue = self.extract_speaker_and_dialogue(dialogue_element.get('content', ''))
                        dialogue_element['Speaker'] = speaker
                        dialogue_element['Dialogue'] = dialogue



                    if csvwriter is None:
                        # Initialize CSV writer and write headers on first iteration
                        fieldnames = list(dialogue_element.keys())
                        csvwriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        csvwriter.writeheader()

                    csvwriter.writerow(dialogue_element)
                    
    def extract_speaker_and_dialogue(self, text):
        dialogue_pattern = re.compile(r"\*'''(.*?):'''\s*(.*)$")  # Captures everything after the speaker's colon to the end of the line)
        match = dialogue_pattern.search(text)
        if match:
            speaker = match.group(1).strip()
            dialogue = match.group(2).strip()
            # Manually replace double single quotes with single quote within the dialogue
            dialogue = re.sub(r"''", "'", dialogue)
            return speaker, dialogue
        else:
            return None, None

    def save_dialogues_to_csv(self, output_csv_file):
        """
        Save all structured dialogues to a CSV file.
        :param output_csv_file: The path to the output CSV file.
        """
        with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = None
            for quest in self.data:
                quest_name = quest.get('Quest_Name', 'UnknownQuest')
                structured_dialogue = quest.get('Structured_Dialogue', [])

                for dialogue_element in structured_dialogue:
                    dialogue_element['Quest_Name'] = quest_name  # Add QuestName to each dialogue element
                    if csvwriter is None:
                        # Initialize CSV writer and write headers on first iteration
                        fieldnames = list(dialogue_element.keys())
                        csvwriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        csvwriter.writeheader()

                    csvwriter.writerow(dialogue_element)
    
    def process_and_update_dialogues(self):
        """
        Process and update dialogues for each quest that contains 'Section_Dialogue'.
        """
        count_not_found = 0
        count_structured_missing = 0
        for quest in self.data:
            quest_name = quest.get('Quest_Name', 'UnknownQuest')
            dialogue_text = quest.get('Section_Dialogue')
            if dialogue_text:
                structurer = DialogueDataStructurer(quest)
                structured_dialogue = structurer.process_dialogue(quest_name, dialogue_text)
                if structured_dialogue:
                    quest['Structured_Dialogue'] = structured_dialogue
                else:
                    logging.warning(f"Structured dialogue missing for quest: {quest_name}")
                    count_structured_missing += 1
            else:
                logging.info(f"No 'Section_Dialogue' found for quest: {quest_name}")
                count_not_found += 1

        print(f"Number of quests without 'Section_Dialogue': {count_not_found}")
        print(f"Number of quests with missing structured dialogues: {count_structured_missing}")

        categorized_quests = self.categorize_quests()
        print(f"Number of quests without 'Section_Dialogue': {count_not_found}")
        self.save_categorized_quests(categorized_quests)

    def save_categorized_quests(self, categorized_quests):
        """
        Save categorized quests into respective folders.
        :param categorized_quests: Dictionary of categorized quests.
        """
        for folder_name, quests in categorized_quests.items():
            self.save_quests_in_folder(quests, folder_name)
            
    def categorize_quests(self):
        """
        Categorize quests based on certain criteria.
        """
        categorized_quests = {
            'quests_with_nested_tabbers': [],
            'quest_with_only_tabbers': [],
            'quests_without_nested_tabbers': [],
            'quests_with_tabber_all': [],
            'quests_without_tabber': [],
            'quests_without_dialogue': []
        }

        for quest in self.data:
            structured_dialogue = quest.get('Structured_Dialogue', '')
            if structured_dialogue:
                contains_nested_tabber = any(segment['segment_type'] == 'NestedTabberStart' for segment in structured_dialogue)
                contains_tabber_all = any(segment['segment_type'] == 'TabberStart' for segment in structured_dialogue)
                contains_only_tabber = contains_tabber_all and not contains_nested_tabber

                if contains_nested_tabber:
                    categorized_quests['quests_with_nested_tabbers'].append(quest)
                elif contains_only_tabber:
                    categorized_quests['quest_with_only_tabbers'].append(quest)
                else:
                    categorized_quests['quests_without_nested_tabbers'].append(quest)

                if contains_tabber_all:
                    categorized_quests['quests_with_tabber_all'].append(quest)
                else:
                    categorized_quests['quests_without_tabber'].append(quest)
            else:
                categorized_quests['quests_without_dialogue'].append(quest)

        return categorized_quests

    def save_quests_in_folder(self, quests, folder_name, main_folder="All_Quests"):
        """
        Save quests in a specified subfolder within a main folder, each quest as a separate JSON file.
        :param quests: List of quests to save.
        :param folder_name: Name of the subfolder to save the quests in.
        :param main_folder: Name of the main folder to contain all subfolders.
        """
        main_folder_path = os.path.join(os.getcwd(), main_folder)
        if not os.path.exists(main_folder_path):
            os.makedirs(main_folder_path)

        subfolder_path = os.path.join(main_folder_path, folder_name)
        if not os.path.exists(subfolder_path):
            os.makedirs(subfolder_path)

        for quest in quests:
            quest_name = self.sanitize_filename(quest.get('Quest_Name', 'UnknownQuest'))
            file_path = os.path.join(subfolder_path, f'{quest_name}.json')
            with open(file_path, 'w', encoding="utf-8") as f:
                json.dump(quest, f, indent=4)
                
    def save_quests_by_index_with_QuestName(self, start, end, output_file_path):
        """
        Save quests by index range to a JSON file.
        :param start: Start index.
        :param end: End index.
        :param output_file_path: Path to the output JSON file.
        """
        quests = self.get_quests_by_range(start, end)
        for quest in quests:
            quest.pop('Quest_Name', None)
            
        with open(output_file_path, 'w', encoding="utf-8") as f:
            json.dump(quests, f, indent=4)
            
    @staticmethod
    def sanitize_value(value):
        """Sanitize a given value by removing or replacing specific characters."""
        if isinstance(value, str):
            # Replace [[ and ]] with nothing
            value = value.replace('[[', '').replace(']]', '')
            # Replace double quotes with nothing or single quotes
            value = value.replace("''", "'")
        return value
    
    @staticmethod
    def is_essentially_null(value):
        """
        Check if a value is essentially null (empty string or similar).
        """
        return value == "" or value == "''" or value == '""' or value is None

    def count_unique_keys(self, quests):
        key_counts = {}

        def process_element(element, parent_key=''):
            if isinstance(element, dict):
                for key, value in element.items():
                    new_key = f"{parent_key}.{key}" if parent_key else key
                    key_counts[new_key] = key_counts.get(new_key, 0) + 1
                    process_element(value, new_key)
            elif isinstance(element, list):
                for item in element:
                    process_element(item, parent_key)

        for quest in quests:
            process_element(quest)

        return key_counts

    def unique_count(self, quests):
        key_counts = {}
        for quest in quests:
            for key in quest.keys():
                if key not in key_counts:
                    key_counts[key] = 0
                key_counts[key] += 1
        return key_counts
    
    def process_single_quest_dialogue(self, quest_name):
        """
        Process and return structured dialogue for a single quest.
        :param quest_name: Name of the quest to process.
        :return: Structured dialogue of the quest or None if quest is not found.
        """
        quest = self.get_quest_by_name(quest_name)
        if quest:
            dialogue_text = quest.get('Section_Dialogue', '')
            return self.dialogue_structurer.process_dialogue(quest_name, dialogue_text)
        else:
            print(f"Quest with name '{quest_name}' not found.")
            return None

    def get_quest_by_name(self, quest_name):
        """
        Retrieve a quest by its name.
        :param quest_name: Name of the quest to retrieve.
        :return: Quest dictionary or None if not found.
        """
        for quest in self.data:
            if quest.get('Quest_Name') == quest_name:
                return quest
        return None
    
    def delete_replace_sanitize(self):
        self.delete_revision_text()
        self.drop_unnessary_keys()
        self.replace_essentially_null_with_none()
        self.sanitize_memory_infobox()
 
    def return_quests_that_do_not_have_apperance(self):
        quests = []
        for quest in self.data:
            if 'MemoryInfobox' in quest:
                if 'appearance' not in quest['MemoryInfobox']:
                    quests.append(quest)
        for quest in quests:
            print(quest['Quest_Name'])
        return quests       

    def replace_empty_string_with_none_in_memory_infobox(self):
        """
        Replace empty string values with None in the MemoryInfobox of each quest.
        """
        for quest in self.data:
            memory_infobox = quest.get('MemoryInfobox', {})
            for key, value in memory_infobox.items():
                if value == "":
                    memory_infobox[key] = None

    def remove_null_key_values_in_memory_infobox(self):
        """
        Remove null key-value pairs in the MemoryInfobox of each quest.
        """
        for quest in self.data:
            memory_infobox = quest.get('MemoryInfobox', {})
            keys_to_remove = [key for key, value in memory_infobox.items() if value is None]
            for key in keys_to_remove:
                memory_infobox.pop(key, None)
                
    def match_quests_that_with_inside_manual_chapter_folder(self, base_path):
        total_quests = len(self.data)
        processed_count = 0

        for quest in self.data:
            quest_name = self.sanitize_filename(quest['Quest_Name'])
            highest_match_score = 0
            matched_file = None
            matched_folder = None
            matched_parent_folder = None

            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith('.json'):
                        file_name = os.path.splitext(file)[0]
                        match_score = fuzz.partial_ratio(quest_name, file_name)

                        if match_score > highest_match_score:
                            highest_match_score = match_score
                            matched_file = file
                            matched_folder = os.path.basename(root)
                            matched_parent_folder = os.path.basename(os.path.dirname(root))

            if highest_match_score >= 80:  # Assuming 80% as the threshold
                chapter_sequence_id = self.extract_sequence_id(matched_folder)
                quest_sequence_id = self.extract_sequence_id(matched_file)
                chapter_name = self.extract_chapter_name(matched_folder)
                chapter_type = self.determine_chapter_type(matched_parent_folder, base_path)
                quest['Chapter_SequenceID'] = chapter_sequence_id
                quest['Chapter_Name'] = chapter_name
                quest['Chapter_Type'] = chapter_type
                quest["Quest_SequenceID"] = quest_sequence_id

            # Log the progress and matched details
            processed_count += 1
            print(f"Processed {processed_count}/{total_quests} quests. "
                f"Current Quest: '{quest_name}'. "
                f"Match Score: {highest_match_score}. "
                f"Matched File: '{matched_file}'. "
                f"Matched Folder: '{matched_folder}'. "
                f"Chapter Type: '{chapter_type}'.")

    def extract_sequence_id(self, name):
        """
        Extracts the sequence ID from a given name (file or folder).
        The sequence ID can be in formats like '1.', '2.a', '14.b', etc.
        """
        sequence_id_pattern = r"^\d+\.?[a-z]*"
        match = re.match(sequence_id_pattern, name)
        if match:
            return match.group()
        return None
    
    def find_unmatched_quests_in_folder(self, base_path):
        # Create a set of all quest filenames (without extension) in the folder
        all_quest_filenames = set()
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith('.json'):
                    filename_without_extension = os.path.splitext(file)[0]
                    all_quest_filenames.add(filename_without_extension)

        # Iterate over your data and remove matched quests from the set
        for quest in self.data:
            quest_name_sanitized = self.sanitize_filename(quest['Quest_Name'])
            all_quest_filenames.discard(quest_name_sanitized)

        # The remaining set contains the filenames of unmatched quests
        return all_quest_filenames
    
    def match_quests_in_odyssey_chapters(self, base_path):
        odyssey_chapters_path = os.path.join(base_path, "Odyssey Chapters")
        unmatched_quests = set([quest['Quest_Name'] for quest in self.data])

        for root, dirs, files in os.walk(odyssey_chapters_path):
            for file in files:
                if file.endswith('.json'):
                    file_name = os.path.splitext(file)[0]
                    for quest_name in unmatched_quests.copy():  # Iterate over a copy to modify the original set
                        quest_name_sanitized = self.sanitize_filename(quest_name)
                        match_score = fuzz.partial_ratio(quest_name_sanitized, file_name)
                        if match_score >= 80:
                            self.update_quest_details(quest_name, root, file)
                            unmatched_quests.discard(quest_name)
        return unmatched_quests
    
    def update_quest_details(self, quest_name, folder_path, file_name):
        for quest in self.data:
            if quest['Quest_Name'] == quest_name:
                folder_name = os.path.basename(folder_path)
                chapter_name, chapter_sequence_id = self.split_folder_name(folder_name)
                quest['ChapterName'] = chapter_name
                quest['ChapterSequenceID'] = chapter_sequence_id
                quest['QuestSequenceID'] = self.extract_sequence_id(file_name)

    def split_folder_name(self, folder_name):
        """
        Splits the folder name into chapter name and sequence ID.
        """
        match = re.match(r"(\d+\.?[a-z]*) (.*)", folder_name)
        if match:
            return match.group(2), match.group(1)  # Chapter name, Sequence ID
        return folder_name, None

    def extract_sequence_id(self, name):
        """
        Extracts the sequence ID from a given name (file or folder).
        """
        sequence_id_pattern = r"^\d+\.?[a-z]*"
        match = re.match(sequence_id_pattern, name)
        if match:
            return match.group()
        return None
    
    def read_folder_structure(self, base_path):
        file_paths = {}
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith('.json'):  # Assuming JSON files
                    file_paths[file] = os.path.join(root, file)
        return file_paths

    def match_quests_with_files(self, file_paths):
        matched_quests = []
        unmatched_quests = []
        for quest in self.data:
            quest_name = self.sanitize_filename(quest.get('Quest_Name'))
            file_path = file_paths.get(quest_name + '.json')
            if file_path:
                matched_quests.append(quest)
                # Add additional details like file_path if needed
            else:
                unmatched_quests.append(quest)
        return matched_quests, unmatched_quests
    
    def extract_chapter_name(self, folder_name):
    # Extract the chapter name, removing numeric prefix unless it has a letter suffix
        match = re.match(r'^(\d+\.?[a-z]*\s)?(.+)$', folder_name)
        if match:
            return match.group(2) if match.group(1) is None or not match.group(1).endswith('.') else folder_name
        return folder_name
    
    def determine_chapter_type(self, parent_folder_name, base_path):
    # Determine the chapter type based on folder structure
        if parent_folder_name == os.path.basename(base_path):
            return None  # Or return '' if you prefer an empty string
        else:
            return parent_folder_name.replace('_', ' ')
    
    def drop_unnessary_keys(self):
        for quest in self.data:
            quest.pop('Revision', None)
            quest.pop('Section_Gallery', None)
            
    def get_quests_by_chapter_type(self, chapter_type):
        """
        Get quests by chapter type.
        :param chapter_type: The chapter type to match.
        :return: List of quests with the specified chapter type.
        """
        matching_quests = []
        for quest in self.data:
            if quest.get('Chapter_Type') == chapter_type:
                matching_quests.append(quest)
        json_file_path = f"{chapter_type}.json"
        with open(json_file_path, 'w', encoding="utf-8") as f:
            json.dump(matching_quests, f, indent=4)
            return matching_quests
            
    
            
odyssey_apperances  = [
    "''[[Assassin's Creed: Odyssey]]''",
    "''[[Assassin's Creed: Odyssey]] – [[The Lost Tales of Greece]]''",
    "''[[Assassin's Creed: Odyssey]]  [[The Lost Tales of Greece]]''",
    "''[[Assassin's Creed: Odyssey]]'' – ''[[Legacy of the First Blade: Hunted]]''",
    "''[[Assassin's Creed: Odyssey]]'' - ''[[Legacy of the First Blade: Hunted]]''",
    "''[[Assassin's Creed: Odyssey]]'' – ''[[Legacy of the First Blade: Shadow Heritage]]''",
    "''[[Assassin's Creed: Odyssey]] – [[Legacy of the First Blade: Shadow Heritage]]''",
    "''[[Assassin's Creed: Odyssey]]'' – ''[[Legacy of the First Blade]]''",
    "''[[Assassin's Creed: Odyssey]]'' – ''[[Legacy of the First Blade: Bloodline]]''",
    "''[[Assassin's Creed: Odyssey]] – [[Legacy of the First Blade: Bloodline]]''",
    "''[[Assassin's Creed: Odyssey]] – [[Legacy of the First Blade: Hunted]]''",
    "''[[Assassin's Creed: Odyssey]]'' - ''[[The Fate of Atlantis: Fields of Elysium]]''",
    "''[[Assassin's Creed: Odyssey]] – [[The Fate of Atlantis: Fields of Elysium]]''",
    "''[[Assassin's Creed: Odyssey]]'' – ''[[The Fate of Atlantis: Fields of Elysium]]''",
    "''[[Assassin's Creed: Odyssey]]'' – ''[[The Fate of Atlantis: Torment of Hades]]''",
    "''[[Assassin's Creed: Odyssey]] – [[The Fate of Atlantis: Torment of Hades]]''",
    "''[[Assassin's Creed: Odyssey]]'' - ''[[The Fate of Atlantis: Torment of Hades]]''",
    "''[[Assassin's Creed: Odyssey]] - [[The Fate of Atlantis: Torment of Hades]]''",
    "''[[Assassin's Creed: Odyssey]]'' – ''[[The Fate of Atlantis: Judgment of Atlantis]]''",
    "''[[Assassin's Creed: Odyssey]] – [[The Fate of Atlantis: Judgment of Atlantis]]''",
    "''[[Assassin's Creed: Odyssey]]'' — ''[[The Fate of Atlantis: Judgment of Atlantis]]''",
    "''[[Assassin's Creed: Odyssey]] - [[The Fate of Atlantis: Judgment of Atlantis]]''",
    "''[[Assassin's Creed: Odyssey]] – [[Assassin's Creed Crossover Stories]]''",
    "''[[Assassin's Creed: Odyssey]] – [[The Lost Tales of Greece]]''"
]

valhalla_apperances = [
    "''[[Assassin's Creed: Valhalla]]''",
    "''[[Assassin's Creed: Valhalla]] – [[The Legend of Beowulf]]''",
    "''[[Assassin's Creed: Valhalla]] – [[The Way of the Berserker]]''",
    "''[[Assassin's Creed: Valhalla]]'' – ''[[River Raids]]''",
    "''[[Assassin's Creed: Valhalla]]'' – ''[[Wrath of the Druids]]''",
    "''[[Assassin's Creed: Valhalla]] – [[Wrath of the Druids]]''",
    "''[[Assassin's Creed: Valhalla]]'' — ''[[Wrath of the Druids]]''",
    "''[[Assassin's Creed: Valhalla]] – [[Mastery Challenge]]''",
    "''[[Assassin's Creed: Valhalla]] – [[The Siege of Paris]]''",
    "''[[Assassin's Creed: Valhalla]]'' – ''[[The Siege of Paris]]''",
    "''[[Discovery Tour: Viking Age]]''",
    "''[[Assassin's Creed: Valhalla]] – [[Assassin's Creed Crossover Stories]]''",
    "''[[Assassin's Creed: Valhalla]]'' – ''[[Assassin's Creed Crossover Stories]]''",
    "''[[Assassin's Creed: Valhalla]] – [[Dawn of Ragnarök]]''",
    "''[[Assassin's Creed: Valhalla]] – [[Mastery Challenge|Mastery Challenge: The Reckoning]]''",
    "''[[Assassin's Creed: Valhalla]] – [[The Forgotten Saga]]''",
    "''[[Assassin's Creed: Valhalla]] – [[Shared History]]''",
    "''[[Assassin's Creed: Valhalla]] – [[The Last Chapter]]''"
]

data_manipulator_new = DataManipulator("Memories relived using the Animus HR-8.5.json")
data_manipulator_new.save_quests_by_memory_infobox_values("appearance", odyssey_apperances, "odysseys.json")
data_manipulator_new.save_quests_by_memory_infobox_values("appearance", valhalla_apperances, "valhalla.json")
data_manipulator_new.delete_replace_sanitize()
data_manipulator_new.replace_empty_string_with_none_in_memory_infobox()
data_manipulator_new.save_json("AllQuestsCleaned.json")

data_manipulator_odyssey = DataManipulator("odysseys.json")
data_manipulator_odyssey.delete_replace_sanitize()
data_manipulator_odyssey.replace_empty_string_with_none_in_memory_infobox()
data_manipulator_odyssey.remove_null_key_values_in_memory_infobox()
data_manipulator_odyssey.save_json("odysseyNew.json")

data_manipulator_odyssey = DataManipulator("odysseyNew.json")
#data_manipulator_odyssey.match_quests_in_odyssey_chapters("Manual Chapterin")
#data_manipulator_odyssey.save_json("odysseychapter.json")

for key,value in data_manipulator_odyssey.count_unique_keys(data_manipulator_odyssey.data).items():
    for quest in data_manipulator_odyssey.data:
        if quest['Quest_Name'] == key:
            print(quest['Quest_Name'])    
    print(key,value)


data_manipulator_odyssey.match_quests_that_with_inside_manual_chapter_folder("Manual Chapterin")
data_manipulator_odyssey.drop_unnessary_keys()
data_manipulator_odyssey.save_json("OdysseyChapterAndSequenceAdded.json")
data_manipulator_odyssey.process_and_update_dialogues()
data_manipulator_odyssey.save_json("OdysseyChapterAndSequenceStructuredDialogue.json")
data_manipulator_odyssey.save_dialogues_to_csv("dialoguesNew.csv")
data_manipulator_odyssey.save_dialogues_to_csv1("dialoguesNew1.csv")
#data_manipulator_odyssey.save_json("odysseyNews.json")

#print(data_manipulator_odyssey.get_length())
print("===========================================" + "\n")
data_manipulator_last = DataManipulator("OdysseyChapterAndSequenceAdded.json")
data_manipulator_last.get_quests_by_chapter_type("Odyssey Chapter")
data_manipulator_last.get_quests_by_chapter_type("Character")
data_manipulator_last.get_quests_by_chapter_type("World")
data_manipulator_last.get_quests_by_chapter_type("The Lost Tales of Greece")
data_manipulator_last.get_quests_by_chapter_type("DLC Chapters")
data_manipulator_last.get_quests_by_chapter_type("Other")



""" Valhalla
data_manipulator_valhalla = DataManipulator("valhalla.json")
data_manipulator_valhalla.delete_replace_sanitize()
data_manipulator_valhalla.replace_empty_string_with_none_in_memory_infobox()
data_manipulator_valhalla.save_json("valhallaNew.json")
for key,value in data_manipulator_valhalla.count_unique_keys(data_manipulator_valhalla.data).items():
    print(key,value)
"""

""" Source Filter Kassandra
# Initialize the DataManipulator with your JSON file
data_manipulator = DataManipulator("Memories relived using the Animus HR-8.5.json")
print(data_manipulator.get_length())
print(data_manipulator.get_unique_source_appearance_pairs())
print("===========================================")

print(data_manipulator.get_unique_values_for_memory_infobox_key("source"))
print("===========================================" + "\n")


print(data_manipulator.get_unique_values_for_memory_infobox_key("appearance"))
print("===========================================" + "\n")

print(data_manipulator.get_unique_values_for_memory_infobox_key("type"))
print("===========================================" + "\n")

# Define the key for filtering and the list of values to filter by
key = "source"
filter_sources = [
    "[[Kassandra]]",
    "[[Kassandra]], [[Layla Hassan]]",
    "[[Alexios|Deimos]]",
    "[[Leonidas I of Sparta]]"
    "[[Deimos]]",
]
# We are only taking quests with the above sources into consideration


# Call the method to filter and save the quests
output_file_path = "onlyKassandraQuests.json"
data_manipulator.save_quests_by_memory_infobox_values(key, filter_sources, output_file_path)
print("===========================================")
print(f"Filtered quests saved to {output_file_path}")
"""

""" Appearance Filter Odyssey
data_manipulator.save_quests_by_memory_infobox_values("appearance", ["''[[Assassin's Creed: Odyssey]]''"], "onlyAppearanceACOdyssey.json")
data_manipulator2 = DataManipulator("onlyAppearanceACOdyssey.json")
print(data_manipulator2.get_length())
data_manipulator2.get_unique_source_appearance_pairs()
data_manipulator2.get_unique_values_for_memory_infobox_key("source")
print(data_manipulator2.get_unique_values_for_memory_infobox_key("source"))
print(data_manipulator2.get_unique_values_for_memory_infobox_key("appearance"))
"""


"""
data_manipulator1 = DataManipulator("onlyKassandraQuests.json")
print(data_manipulator1.get_unique_source_appearance_pairs())
print(data_manipulator1.count_unique_keys(data_manipulator1.data))
print(data_manipulator1.unique_count(data_manipulator1.data))
print(data_manipulator1.get_unique_values_for_memory_infobox_key("appearance"))
print(data_manipulator1.get_unique_values_for_memory_infobox_key("type"))

for key,value in data_manipulator1.count_unique_keys(data_manipulator1.data).items():
    print(key,value)
        
print(data_manipulator1.get_length())
data_manipulator1.delete_revision_text()
data_manipulator1.replace_essentially_null_with_none()
data_manipulator1.sanitize_memory_infobox()

data_manipulator1.save_json("OnlyKassandraSanitizedAndCleaned.json")
data_manipulator = DataManipulator("OnlyKassandraSanitizedAndCleaned.json")
data_manipulator.process_and_update_dialogues()
data_manipulator.get_dialogue_by_index(0) 
data_manipulator.get_dialogue_by_name("A Fresh Start")
data_manipulator.save_quests_by_index(0, 1, "test.json")
data_manipulator.save_json("idsegment.json")
data_manipulator.save_dialogues_to_csv("dialoguesNew.csv")
"""

"""
data_manipulator.get_structured_dialogue_by_index(0)
for each in data_manipulator.get_structured_dialogue_by_index(0):
    print(each)
""" 

"""
b = data_manipulator_odyssey.get_length()
a = data_manipulator_valhalla.get_length()

print(a)
print(b)
print(a+b)

"""