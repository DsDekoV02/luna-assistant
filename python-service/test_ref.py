import wave, sys
sys.stdout.reconfigure(encoding='utf-8')
ref = r"D:\LunaDrive\LunaLab\projects\luna-jarvis\experiments\luna_voz_v5b_kohana_fina.wav"
with wave.open(ref, 'rb') as wf:
    dur = wf.getnframes() / wf.getframerate()
    print(f"Duration: {dur:.2f}s")
    print(f"Channels: {wf.getnchannels()}")
    print(f"Rate: {wf.getframerate()}Hz")
    print(f"Sample width: {wf.getsampwidth()} bytes")

# Test text processor bug
sys.path.insert(0, r"D:\LunaDrive\LunaLab\projects\luna-jarvis\python-service")
from voice.text_processor import optimize_for_voice_clone
test = "Hola Nicolas, como estas hoy?"
result = optimize_for_voice_clone(test)
print(f"\nText processor test:")
print(f"  Input:  '{test}'")
print(f"  Output: '{result}'")
print(f"  Match: {test == result}")