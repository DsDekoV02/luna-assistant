import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"D:\LunaDrive\LunaLab\projects\luna-jarvis\python-service")

from brain.mimo_client import MiMoClient
from voice.text_processor import optimize_for_voice_clone

VOICE_REF = r"D:\LunaDrive\LunaLab\projects\luna-jarvis\experiments\luna_voz_v5b_kohana_fina.wav"

client = MiMoClient()

# Test the same phrase that Nicolas liked (test 4)
test_text = "Buenos dias Dekov, espero que tengas un excelente dia."
processed = optimize_for_voice_clone(test_text)

print(f"Original:  '{test_text}'")
print(f"Processed: '{processed}'")
print(f"Match: {test_text == processed}")

# Generate audio
print("\nGenerating voice clone...")
audio = client.voice_clone(processed, VOICE_REF)
size_kb = len(audio) / 1024
print(f"Audio size: {size_kb:.1f} KB")

# Save
output_path = r"D:\LunaDrive\LunaLab\projects\luna-jarvis\experiments\test_original_ref.wav"
with open(output_path, "wb") as f:
    f.write(audio)
print(f"Saved to: {output_path}")