"""E2E test for Luna JARVIS - Session 38"""
import requests
import json
import sys
import os

# Fix encoding for Windows console
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE = "http://localhost:8765"

def test_health():
    r = requests.get(f"{BASE}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("healthy", "degraded"), f"Unexpected status: {data['status']}"
    print(f"[OK] Health: {data['status']}, RAG: {data['rag']['total_chunks']} chunks, Mode: {data['mode']['mode']}")
    return True

def test_chat(message, expected_emotion=None):
    r = requests.post(f"{BASE}/chat", json={
        "message": message,
        "use_rag": True
    }, timeout=60)
    assert r.status_code == 200
    data = r.json()
    emotion = data["emotion"]["primary"]
    confidence = data["emotion"]["confidence"]
    intensity = data["emotion"]["intensity"]
    response = data["response"][:150].encode('ascii', 'replace').decode('ascii')
    
    status = "OK" if (expected_emotion is None or emotion == expected_emotion) else "MISMATCH"
    print(f"[{status}] Emotion: {emotion} (conf={confidence}, int={intensity}) | Expected: {expected_emotion}")
    print(f"  Response: {response}...")
    
    if expected_emotion and emotion != expected_emotion:
        print(f"  WARNING: Got {emotion}, expected {expected_emotion}")
    
    return data

def test_tts_edge(text):
    r = requests.post(f"{BASE}/tts", json={
        "text": text,
        "use_edge": True
    }, timeout=60)
    assert r.status_code == 200
    data = r.json()
    audio_size = data.get("size", 0)
    print(f"[OK] Edge TTS: {audio_size} bytes")
    
    # Save to file for testing
    import base64
    audio_bytes = base64.b64decode(data["audio"])
    out_path = "test_tts_output.wav"
    with open(out_path, "wb") as f:
        f.write(audio_bytes)
    print(f"  Saved: {out_path} ({len(audio_bytes)} bytes)")
    return True

def test_emotion_detection():
    """Test multiple emotions."""
    cases = [
        ("Estoy muy feliz, todo perfecto!", "happy"),
        ("No puedo creer que pasara eso, en serio?", "surprised"),
        ("No entiendo nada de esto, me tiene confundido", "confused"),
        ("Que lindo dia, gracias por todo!", "grateful"),
        ("Estoy cansado, llevo todo el dia trabajando", "tired"),
        ("Hola, como estas?", None),  # neutral
    ]
    
    print("\n=== Emotion Detection Tests ===")
    for msg, expected in cases:
        test_chat(msg, expected)
        print()

def test_conversations():
    r = requests.get(f"{BASE}/conversations", timeout=30)
    assert r.status_code == 200
    data = r.json()
    print(f"[OK] Conversations: {len(data['sessions'])} sessions")
    return True

def test_emotion_stats():
    r = requests.get(f"{BASE}/emotion/stats", timeout=30)
    assert r.status_code == 200
    data = r.json()
    print(f"[OK] Emotion stats: {data}")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Luna JARVIS - E2E Test (Session 38)")
    print("=" * 60)
    
    # 1. Health check
    print("\n--- Health Check ---")
    if not test_health():
        print("FATAL: Health check failed")
        sys.exit(1)
    
    # 2. Basic chat
    print("\n--- Basic Chat ---")
    test_chat("Hola Luna, buenos dias!")
    
    # 3. Emotion detection
    test_emotion_detection()
    
    # 4. TTS test (Edge)
    print("\n--- Edge TTS Test ---")
    test_tts_edge("Hola Nicolas, soy Luna. Estoy aqui para ayudarte.")
    
    # 5. Conversations
    print("\n--- Conversations ---")
    test_conversations()
    
    # 6. Emotion stats
    print("\n--- Emotion Stats ---")
    test_emotion_stats()
    
    print("\n" + "=" * 60)
    print("All E2E tests completed!")
    print("=" * 60)
