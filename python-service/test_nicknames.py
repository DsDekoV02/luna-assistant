import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"D:\LunaDrive\LunaLab\projects\luna-jarvis\python-service")

from brain.mimo_client import MiMoClient
from voice.text_processor import optimize_for_voice_clone

VOICE_REF = r"D:\LunaDrive\LunaLab\projects\luna-jarvis\experiments\luna_voz_v5b_kohana_fina.wav"

client = MiMoClient()

# Test with natural Luna responses using nicknames
tests = [
    "Hola Dekov, como estas hoy? En que puedo ayudarte?",
    "Salocin, encontre un error en tu codigo de Python.",
    "D, ya termine de revisar el proyecto. Todo esta bien.",
    "Buenos dias Dekov! Espero que tengas un excelente dia.",
]

print("Final Voice Clone Test - With Nicknames")
print("=" * 50)

for i, text in enumerate(tests, 1):
    processed = optimize_for_voice_clone(text)
    print(f"\nTest {i}: '{text}'")
    print(f"  Processed: '{processed}'")
    
    try:
        audio = client.voice_clone(processed, VOICE_REF)
        size_kb = len(audio) / 1024
        print(f"  Audio: {size_kb:.1f} KB - {'OK' if size_kb > 50 else 'CHECK'}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\nDone!")