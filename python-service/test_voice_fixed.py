import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"D:\LunaDrive\LunaLab\projects\luna-jarvis\python-service")

from brain.mimo_client import MiMoClient
from voice.text_processor import optimize_for_voice_clone

VOICE_REF = r"D:\LunaDrive\LunaLab\projects\luna-jarvis\experiments\luna_voz_v5b_kohana_fina.wav"
OUTPUT = r"D:\LunaDrive\LunaLab\projects\luna-jarvis\experiments\voice_clone_fixed"

os.makedirs(OUTPUT, exist_ok=True)

client = MiMoClient()

tests = [
    "Hola Dekov, como estas hoy?",
    "Que tal Salocin, en que puedo ayudarte?",
    "Hola D, soy Luna. Me alegra verte.",
    "Buenos dias Dekov, espero que tengas un excelente dia.",
    "Salocin, tienes 3 mensajes nuevos y la CPU esta al 45 por ciento.",
    "Hola Dekov! Como estas? En que puedo ayudarte hoy?",
]

print("Voice Clone Test - Post Bug Fix")
print("=" * 50)

for i, text in enumerate(tests, 1):
    processed = optimize_for_voice_clone(text)
    print(f"\nTest {i}:")
    print(f"  Original:  '{text}'")
    print(f"  Processed: '{processed}'")
    
    try:
        audio = client.voice_clone(processed, VOICE_REF)
        size_kb = len(audio) / 1024
        filename = f"test_{i}_fixed.wav"
        filepath = os.path.join(OUTPUT, filename)
        with open(filepath, "wb") as f:
            f.write(audio)
        print(f"  Audio: {size_kb:.1f} KB - {'OK' if size_kb > 50 else 'SUSPICIOUS'}")
    except Exception as e:
        print(f"  ERROR: {e}")

print(f"\n{'=' * 50}")
print(f"Archivos guardados en: {OUTPUT}")