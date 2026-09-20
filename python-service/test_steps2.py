import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"D:\LunaDrive\LunaLab\projects\luna-jarvis\python-service")
from voice.text_processor import *

text = "Buenos dias! Que tal todo?"
print(f"Original: '{text}'")
print()

steps = [
    ("expand_percentages", expand_percentages),
    ("expand_time_formats", expand_time_formats),
    ("expand_size_units", expand_size_units),
    ("expand_decimal_numbers", expand_decimal_numbers),
    ("expand_file_urls", expand_file_urls),
    ("expand_file_extensions", expand_file_extensions),
    ("expand_abbreviations", expand_abbreviations),
    ("expand_symbols", expand_symbols),
    ("clean_for_tts", clean_for_tts),
    ("expand_numbers", expand_numbers),
    ("expand_tech_terms", expand_tech_terms),
    ("expand_english_words", expand_english_words),
    ("expand_contractions", expand_contractions),
    ("apply_phonetic_respelling", apply_phonetic_respelling),
    ("normalize_repeated_chars", normalize_repeated_chars),
    ("soften_difficult_clusters", soften_difficult_clusters),
    ("apply_rhythm_breaks", apply_rhythm_breaks),
    ("add_emphasis_markers", add_emphasis_markers),
    ("apply_sentence_prosody", apply_sentence_prosody),
    ("improve_natural_phrases", improve_natural_phrases),
    ("add_prosody_pauses", add_prosody_pauses),
    ("remove_accents", remove_accents),
    ("add_pauses", add_pauses),
]

current = text
for name, func in steps:
    try:
        result = func(current)
        if result != current:
            print(f"  {name}: '{current}' -> '{result}'")
            current = result
    except Exception as e:
        print(f"  {name}: ERROR - {e}")

print(f"\nFinal: '{current}'")