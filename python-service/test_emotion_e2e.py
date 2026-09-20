"""Quick E2E emotion + TTS test."""
import requests
import json
import base64
import os

BASE = "http://127.0.0.1:8765"

# Test 1: Emotion detection via /chat
print("=== Emotion Detection E2E ===")
tests = [
    "Estoy tan cansado, no puedo mas, necesito dormir",
    "No entiendo nada de esto, me tiene confundido",
    "Gracias Luna, eres la mejor!!",
    "Esto no funciona!!! Lleva horas y nada, que frustrante",
    "Hmm, me pregunsto como funciona ese algoritmo",
]

for msg in tests:
    try:
        r = requests.post(f"{BASE}/chat", json={"message": msg}, timeout=25)
        d = r.json()
        e = d.get("emotion", {})
        label = msg[:45]
        print(f"  {label:45s} -> {e.get('primary', '?'):12s} conf={e.get('confidence', 0)} int={e.get('intensity', 0)}")
    except Exception as ex:
        print(f"  ERROR: {ex}")

# Test 2: TTS voice clone
print("\n=== TTS Voice Clone ===")
tts_texts = [
    "Hola Nicolas, soy Luna. Estoy aqui para ayudarte.",
    "Me alegra que estes bien hoy!",
]
for i, text in enumerate(tts_texts):
    try:
        r = requests.post(f"{BASE}/tts", json={"text": text, "use_clone": True}, timeout=30)
        d = r.json()
        if "audio" in d:
            audio_bytes = base64.b64decode(d["audio"])
            out_path = f"../experiments/session23_voice_test_{i+1}.wav"
            os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else ".", exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(audio_bytes)
            print(f"  [{i+1}] Generated: {out_path} ({len(audio_bytes)} bytes)")
        else:
            print(f"  [{i+1}] No audio returned: {d}")
    except Exception as ex:
        print(f"  [{i+1}] ERROR: {ex}")

# Test 3: Health check
print("\n=== System Health ===")
r = requests.get(f"{BASE}/health", timeout=5)
print(f"  Status: {r.json().get('status')}")
print(f"  MiMo: {r.json().get('mimo_api')}")

# Test 4: Emotion stats
r = requests.get(f"{BASE}/emotion/stats", timeout=5)
stats = r.json()
print(f"  Emotions analyzed: {stats.get('total_analyzed', 0)}")
print(f"  Distribution: {stats.get('emotion_distribution', {})}")

# Test 5: Conversation stats
r = requests.get(f"{BASE}/conversations/stats", timeout=5)
conv = r.json()
print(f"  Total messages: {conv.get('total_messages', 0)}")
print(f"  Sessions: {conv.get('total_sessions', 0)}")

print("\n=== DONE ===")