import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"D:\LunaDrive\LunaLab\projects\luna-jarvis\python-service")

from brain.mimo_client import MiMoClient
from voice.text_processor import optimize_for_voice_clone

OUTPUT = r"D:\LunaDrive\LunaLab\projects\luna-jarvis\experiments\voice_design_test"
import os
os.makedirs(OUTPUT, exist_ok=True)

client = MiMoClient()

# Test voice_design vs voice_clone
test_text = "Hola Dekov, como estas hoy? Me alegra mucho verte. Soy Luna, tu asistente."

print("Voice Design vs Voice Clone Comparison")
print("=" * 50)

# Test 1: Voice Design (personality-based)
print("\n1. VOICE DESIGN (personality description):")
descriptions = [
    ("warm_girl", "A warm, friendly young woman with a soft voice, like a close friend"),
    ("calm_assistant", "A calm, professional female assistant with clear pronunciation"),
    ("anime_girl", "A cheerful anime-style girl voice, energetic and sweet"),
]

for label, desc in descriptions:
    try:
        audio = client.voice_design(desc, test_text)
        size_kb = len(audio) / 1024
        filepath = os.path.join(OUTPUT, f"design_{label}.wav")
        with open(filepath, "wb") as f:
            f.write(audio)
        print(f"  {label}: {size_kb:.1f} KB")
    except Exception as e:
        print(f"  {label}: ERROR - {e}")

# Test 2: Voice Clone (reference-based)
print("\n2. VOICE CLONE (reference audio):")
ref_files = [
    ("kohana", r"D:\LunaDrive\LunaLab\projects\luna-jarvis\experiments\luna_voz_v5b_kohana_fina.wav"),
    ("session23", r"D:\LunaDrive\LunaLab\projects\luna-jarvis\experiments\session23_voice_test_1.wav"),
]

for label, ref_path in ref_files:
    try:
        audio = client.voice_clone(test_text, ref_path)
        size_kb = len(audio) / 1024
        filepath = os.path.join(OUTPUT, f"clone_{label}.wav")
        with open(filepath, "wb") as f:
            f.write(audio)
        print(f"  {label}: {size_kb:.1f} KB")
    except Exception as e:
        print(f"  {label}: ERROR - {e}")

# Test 3: Standard TTS (no clone, no design)
print("\n3. STANDARD TTS (default voice):")
try:
    audio = client.tts(test_text)
    size_kb = len(audio) / 1024
    filepath = os.path.join(OUTPUT, "standard_tts.wav")
    with open(filepath, "wb") as f:
        f.write(audio)
    print(f"  standard: {size_kb:.1f} KB")
except Exception as e:
    print(f"  standard: ERROR - {e}")

print(f"\nArchivos guardados en: {OUTPUT}")
print("\nCompara los audios para ver cual suena mejor!")