"""Quick ASR test with real audio files."""
import sys
import os
import io

# Fix Windows console encoding for Unicode output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(__file__))

from brain.mimo_client import get_client

client = get_client()

base = os.path.join(os.path.dirname(__file__), '..', 'experiments')
wav_files = [
    os.path.join(base, 'luna_clone_test_1.wav'),
    os.path.join(base, 'luna_clone_test_2.wav'),
    os.path.join(base, 'luna_clone_test_3.wav'),
    os.path.join(base, 'luna_clone_test_4.wav'),
    os.path.join(base, 'session23_voice_test_1.wav'),
    os.path.join(base, 'session23_voice_test_2.wav'),
]

for wav_path in wav_files:
    if os.path.exists(wav_path):
        size = os.path.getsize(wav_path)
        print(f"\n--- {wav_path} ({size} bytes) ---")
        try:
            text = client.asr(wav_path)
            print(f"ASR: \"{text}\"")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"SKIP: {wav_path} not found")