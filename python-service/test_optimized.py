import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"D:\LunaDrive\LunaLab\projects\luna-jarvis\python-service")

from brain.mimo_client import MiMoClient
from voice.text_processor import optimize_for_voice_clone

# Use the best reference audio found by optimizer
VOICE_REF = r"D:\LunaDrive\LunaLab\projects\luna-jarvis\experiments\session23_voice_test_1.wav"
OUTPUT = r"D:\LunaDrive\LunaLab\projects\luna-jarvis\experiments\voice_optimized"

import os
os.makedirs(OUTPUT, exist_ok=True)

client = MiMoClient()

# Optimal settings from optimizer:
# - Text length: 9-19 words
# - Style: conversational/mixed
# - Punctuation: natural pauses with '...'

tests = [
    ("greeting", "Hola Dekov! Como estas hoy? Me alegra mucho verte."),
    ("help", "Claro que si Dekov, con gusto te ayudo con eso. Dame un momento."),
    ("status", "El sistema esta funcionando bien Dekov. La CPU esta al 45 por ciento."),
    ("farewell", "Buenas noches Dekov, que descanses. Manana seguimos con el proyecto."),
    ("emotional", "Que bueno que viniste Dekov! Estaba esperandote con muchas ganas."),
]

print("Voice Clone Test - Optimized Settings")
print("=" * 50)
print(f"Reference: {os.path.basename(VOICE_REF)}")
print()

for label, text in tests:
    processed = optimize_for_voice_clone(text)
    words = len(processed.split())
    print(f"{label} ({words} words):")
    print(f"  Text: '{processed}'")
    
    try:
        audio = client.voice_clone(processed, VOICE_REF)
        size_kb = len(audio) / 1024
        filename = f"opt_{label}.wav"
        filepath = os.path.join(OUTPUT, filename)
        with open(filepath, "wb") as f:
            f.write(audio)
        print(f"  Audio: {size_kb:.1f} KB - {'OK' if size_kb > 50 else 'CHECK'}")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()

print(f"Archivos guardados en: {OUTPUT}")