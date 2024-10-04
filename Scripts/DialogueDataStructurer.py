from msilib import sequence
import re
import json
import uuid
from enum import Enum
from collections import defaultdict


class SegmentType(Enum):
    DIALOGUE = "Dialogue"
    PLAYER_CHOICE = "PlayerChoice"
    NARRATIVE = "Narrative"
    CONDITION = "Condition"
    TABBER_START = "TabberStart"
    TABBER_END = "TabberEnd"
    NESTED_TABBER_START = "NestedTabberStart"
    NESTED_CHOICE_DELIMITER = "NestedChoiceDelimiter"
    NESTED_TABBER_END = "NestedTabberEnd"
    OPTIONAL_CHOICE = "OptionalChoice"
    IMG_FILE = "ImageFile"
    UNIDENTIFIED = "Unidentified"

regex_patterns = {
    SegmentType.DIALOGUE: re.compile(
        r"\*'''(.*?):'''(?:\s*''(.*?)''|\s*(.*?)$)|"  # Standard dialogue format and without quotes
        r"\*\*'''(.*?):'''(?:\s*''(.*?)''|$)|"  # Double asterisk before character name
        r"\* '''(.*?):'''(?:\s*''(.*?)''|$)|"  # Single quote and space before character name
        r"\*'''(.*?)'''(?:\s*''(.*?)''|$)|"  # Triple quotes around character name
        r"\*'''(.*?)''':\s*''(.*?)''|"  # Mixed quote usage within dialogue
        r"\*\*'''(.*?)''',?''(?:\s*''(.*?)''|$)|"  # Double asterisk and mixed quote usage
        r"\*'''([^']*?)'''\s*'''([^']*?)'''|"  # Multiple triple quotes in dialogue
        r"\*'''(.*?)'''\s*''(.*?)''"  # Single triple quote in dialogue

    ),  # Triple quotes around character name

    SegmentType.PLAYER_CHOICE: re.compile(r"\|-|\s*(.*)="),
    SegmentType.NARRATIVE: re.compile(r"^[^*|<\(\{].*$"),
    SegmentType.CONDITION: re.compile(
        r'\(If ".*" (is|was)?\s*(chosen|asked|choose)?[.?!"\']?\)|'
        r'\(If players (choose|chose|asked) ".*"[.?!"\']?\)|'
        r'\(Asked ".*"[.?!"\']?\)|'
        r'\(-> ".*"[.?!"\']?\)|'
        r'\(If ".*" was chosen[.?!"\']?\)|'
        r'\((Chose|Choose) ".*"[.?!"\']?\)|'
        r"\(If players? .*\)|"
        r"\*\*(If players choose .*)|"  # Added pattern for condition with double asterisk
        r"\*(If players met .*)|"  # Added pattern for specific condition format
        r"\*(If players went straight to .*)"  # Added pattern for another condition format

    ),
    SegmentType.TABBER_START: re.compile(r"<Tabber>|<tabber>"),  # Adjusted for case-insensitivity
    SegmentType.TABBER_END: re.compile(r"</Tabber>|</tabber>"),  # Adjusted for case-insensitivity
    SegmentType.NESTED_TABBER_START: re.compile(r"\{\{#tag:tabber\||\{\{#tag: tabber\|"),
    SegmentType.NESTED_CHOICE_DELIMITER: re.compile(r"\{\{!\}\}-\{\{!\}\}"),
    SegmentType.NESTED_TABBER_END: re.compile(r"\}\}"),
    SegmentType.OPTIONAL_CHOICE: re.compile(r"\(.*\)"),
    SegmentType.IMG_FILE: re.compile(        r"\[\[File:.*?\|thumb\|\d+px\|.*?\]\]")


}

class DialogueDataStructurer:
    def __init__(self, quest_data):
        self.quest_data = quest_data
        self.regex_patterns = regex_patterns
        self.global_counter = 0  # Global counter for all segments
        self.prefix_to_counter = {
            "D": "dialogue_counter",
            "N": "narrative_counter",
            "PC": "choice_counter",
            "C": "condition_counter",
            "O": "optional_choice_counter",
            "TS": "tabber_start_counter",
            "TE": "tabber_end_counter",
            "NTS": "nested_tabber_start_counter",
            "NTD": "nested_tabber_delimiter_counter",
            "NTE": "nested_tabber_end_counter",
            "I": "image_counter",
            "U": "unidentified_counter"  # Added counter for 'U' - Unidentified
        }
        self.segment_counters = {counter: 0 for counter in self.prefix_to_counter.values()}
    
    def identify_segment_type(self, line):
        # Check for specific segment types first
        for segment_type in [SegmentType.DIALOGUE, SegmentType.PLAYER_CHOICE, 
                            SegmentType.CONDITION, SegmentType.TABBER_START, 
                            SegmentType.TABBER_END, SegmentType.NESTED_TABBER_START, 
                            SegmentType.NESTED_TABBER_END, SegmentType.NESTED_CHOICE_DELIMITER, SegmentType.IMG_FILE]:
            pattern = self.regex_patterns[segment_type]
            if pattern.match(line):
                return segment_type
            
        if self.regex_patterns[SegmentType.OPTIONAL_CHOICE].match(line):
            return SegmentType.OPTIONAL_CHOICE

        # If none of the specific types match, check for NARRATIVE
        elif self.regex_patterns[SegmentType.NARRATIVE].match(line):
            return SegmentType.NARRATIVE

        # If no pattern matches, return UNIDENTIFIED
        return SegmentType.UNIDENTIFIED
    
    def get_prefix(self, segment_type):
        # Map SegmentType to its corresponding prefix
        prefix_mapping = {
            SegmentType.DIALOGUE: "D",
            SegmentType.PLAYER_CHOICE: "PC",
            SegmentType.NARRATIVE: "N",
            SegmentType.CONDITION: "C",
            SegmentType.TABBER_START: "TS",
            SegmentType.TABBER_END: "TE",
            SegmentType.NESTED_TABBER_START: "NTS",
            SegmentType.NESTED_CHOICE_DELIMITER: "NTD",
            SegmentType.NESTED_TABBER_END: "NTE",
            SegmentType.OPTIONAL_CHOICE: "O",
            SegmentType.IMG_FILE: "I",
            SegmentType.UNIDENTIFIED: "U"
            # Add other mappings if needed
        }
        return prefix_mapping.get(segment_type, "U")  # "U" for unidentified

    def generate_unique_id(self, segment_type):
        # Map the segment type to its prefix
        prefix = self.get_prefix(segment_type)
        counter_name = self.prefix_to_counter[prefix]
        self.segment_counters[counter_name] += 1
        return f"{prefix}{self.segment_counters[counter_name]}"
    
    def generate_global_id(self):
        self.global_counter += 1
        return str(self.global_counter) 
    
    def process_dialogue(self, quest_name, section_dialogue):
        if section_dialogue is None:
            return []

        lines = section_dialogue.split('\n')
        structured_dialogue = []

        for line in lines:
            segment_type = self.identify_segment_type(line)
            unique_id = self.generate_unique_id(segment_type)
            global_id = self.generate_global_id()

            dialogue_segment = {
                'id': unique_id,
                'global_id': global_id,
                'content': line.strip(),
                'segment_type': segment_type.value,
            }

            structured_dialogue.append(dialogue_segment)

        return structured_dialogue
