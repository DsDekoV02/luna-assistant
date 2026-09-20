#!/usr/bin/env python3
"""
Voice Clone Diagnostic Script
Investiga por qué algunos clones producen basura.
"""

import os
import sys
import json
import time
import base64
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.mimo_client import MiMoClient
from voice.text_processor import optimize_for_voice_clone

VOICE_REF = r"D:\LunaDrive\LunaLab\projects\luna-jarvis\python-service\voice\luna_voz_v5b_kohana_fina.wav"
OUTPUT_DIR = Path(__file__).parent / "voice_diagnostics"
OUTPUT_DIR.mkdir(exist_ok=True)

def test_voice_clone_consistency(client, text, runs=3):
    """Test same text multiple times to check API determinism."""
    print(f"\n=== CONSISTENCY TEST: '{text}' ({runs} runs) ===")
    results = []
    
    for i in range(runs):
        try:
            audio = client.voice_clone(text, VOICE_REF)
            size_kb = len(audio) / 1024
            results.append({"run": i+1, "size_kb": round(size_kb, 1), "ok": size_kb > 10})
            
            # Save audio
            filename = f"consistency_{i+1}.wav"
            filepath = OUTPUT_DIR / filename
            with open(filepath, "wb") as f:
                f.write(audio)
            
            print(f"  Run {i+1}: {size_kb:.1f} KB - {'OK' if size_kb > 10 else 'SUSPICIOUS'}")
            time.sleep(1)  # Rate limit
        except Exception as e:
            print(f"  Run {i+1}: ERROR - {e}")
            results.append({"run": i+1, "error": str(e)})
    
    return results


def test_text_processor_impact(client, original_text):
    """Compare voice clone with and without text processing."""
    print(f"\n=== TEXT PROCESSOR IMPACT ===")
    print(f"Original: '{original_text}'")
    
    processed = optimize_for_voice_clone(original_text)
    print(f"Processed: '{processed}'")
    
    # Show what changed
    if original_text != processed:
        print("CHANGES DETECTED:")
        orig_words = original_text.split()
        proc_words = processed.split()
        for i, (o, p) in enumerate(zip(orig_words, proc_words)):
            if o != p:
                print(f"  Word {i}: '{o}' -> '{p}'")
        if len(orig_words) != len(proc_words):
            print(f"  Word count: {len(orig_words)} -> {len(proc_words)}")
    else:
        print("No changes from text processor")
    
    # Test both versions
    print("\nGenerating ORIGINAL version...")
    try:
        audio_orig = client.voice_clone(original_text, VOICE_REF)
        size_orig = len(audio_orig) / 1024
        with open(OUTPUT_DIR / "original.wav", "wb") as f:
            f.write(audio_orig)
        print(f"  Size: {size_orig:.1f} KB")
    except Exception as e:
        print(f"  ERROR: {e}")
        size_orig = 0
    
    time.sleep(1)
    
    print("Generating PROCESSED version...")
    try:
        audio_proc = client.voice_clone(processed, VOICE_REF)
        size_proc = len(audio_proc) / 1024
        with open(OUTPUT_DIR / "processed.wav", "wb") as f:
            f.write(audio_proc)
        print(f"  Size: {size_proc:.1f} KB")
    except Exception as e:
        print(f"  ERROR: {e}")
        size_proc = 0
    
    return {"original_size_kb": round(size_orig, 1), "processed_size_kb": round(size_proc, 1)}


def test_text_length(client):
    """Test with different text lengths."""
    print(f"\n=== TEXT LENGTH TEST ===")
    
    texts = [
        ("Hola", "short"),
        ("Hola Nicolas, como estas hoy", "medium"),
        ("Hola Nicolas, como estas hoy. En que puedo ayudarte esta manana. Espero que tengas un buen dia.", "long"),
        ("Hola Nicolas. Soy Luna. Estoy aqui para ayudarte. Puedo buscar archivos. Puedo abrir aplicaciones. Puedo responder preguntas. Que necesitas?", "very_long"),
    ]
    
    results = []
    for text, label in texts:
        try:
            audio = client.voice_clone(text, VOICE_REF)
            size_kb = len(audio) / 1024
            filename = f"length_{label}.wav"
            with open(OUTPUT_DIR / filename, "wb") as f:
                f.write(audio)
            results.append({"label": label, "words": len(text.split()), "size_kb": round(size_kb, 1)})
            print(f"  {label} ({len(text.split())} words): {size_kb:.1f} KB")
            time.sleep(1)
        except Exception as e:
            print(f"  {label}: ERROR - {e}")
            results.append({"label": label, "error": str(e)})
    
    return results


def test_special_characters(client):
    """Test with special characters that might cause issues."""
    print(f"\n=== SPECIAL CHARACTERS TEST ===")
    
    tests = [
        ("Hola Nicolas", "clean"),
        ("Hola Nicolas!", "exclamation"),
        ("Hola Nicolas!!!", "multi_exclamation"),
        ("Hola Nicolas... como estas?", "ellipsis"),
        ("Hola Nicolas - como estas?", "dash"),
        ("Hola Nicolas, como estas? En que puedo ayudarte?", "question_marks"),
        ("Hola Nicolas (soy Luna)", "parentheses"),
        ("Hola Nicolas: te ayudo?", "colon"),
        ("Hola Nicolas; soy Luna", "semicolon"),
    ]
    
    results = []
    for text, label in tests:
        try:
            audio = client.voice_clone(text, VOICE_REF)
            size_kb = len(audio) / 1024
            filename = f"special_{label}.wav"
            with open(OUTPUT_DIR / filename, "wb") as f:
                f.write(audio)
            results.append({"label": label, "size_kb": round(size_kb, 1), "ok": size_kb > 10})
            print(f"  {label}: {size_kb:.1f} KB - {'OK' if size_kb > 10 else 'SUSPICIOUS'}")
            time.sleep(1)
        except Exception as e:
            print(f"  {label}: ERROR - {e}")
            results.append({"label": label, "error": str(e)})
    
    return results


def analyze_reference_audio():
    """Analyze the reference audio file."""
    print(f"\n=== REFERENCE AUDIO ANALYSIS ===")
    
    if not Path(VOICE_REF).exists():
        print(f"ERROR: Reference file not found: {VOICE_REF}")
        return None
    
    size_bytes = Path(VOICE_REF).stat().st_size
    size_kb = size_bytes / 1024
    
    # Try to read WAV header
    try:
        import wave
        with wave.open(VOICE_REF, 'rb') as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            frames = wf.getnframes()
            duration = frames / framerate
            
            print(f"  File: {VOICE_REF}")
            print(f"  Size: {size_kb:.1f} KB")
            print(f"  Channels: {channels}")
            print(f"  Sample width: {sample_width} bytes")
            print(f"  Framerate: {framerate} Hz")
            print(f"  Duration: {duration:.2f} seconds")
            print(f"  Frames: {frames}")
            
            # Check if duration is reasonable (1-30 seconds ideal for voice clone)
            if duration < 1:
                print("  WARNING: Audio too short (< 1s). Voice clone quality may suffer.")
            elif duration > 30:
                print("  WARNING: Audio too long (> 30s). May cause API issues.")
            else:
                print("  OK: Duration looks good for voice clone.")
            
            return {
                "size_kb": round(size_kb, 1),
                "channels": channels,
                "sample_width": sample_width,
                "framerate": framerate,
                "duration": round(duration, 2)
            }
    except Exception as e:
        print(f"  ERROR reading WAV: {e}")
        return None


def main():
    print("Voice Clone Diagnostic Tool")
    print("=" * 50)
    
    # Analyze reference audio
    ref_info = analyze_reference_audio()
    
    # Initialize client
    client = MiMoClient()
    
    # Run tests
    all_results = {}
    
    # 1. Reference audio analysis
    all_results["reference"] = ref_info
    
    # 2. Consistency test
    all_results["consistency"] = test_voice_clone_consistency(client, "Hola Nicolas, como estas?")
    
    # 3. Text processor impact
    all_results["processor"] = test_text_processor_impact(client, "Hola Nicolas, como estas hoy?")
    
    # 4. Text length test
    all_results["length"] = test_text_length(client)
    
    # 5. Special characters test
    all_results["special_chars"] = test_special_characters(client)
    
    # Save results
    results_path = OUTPUT_DIR / "diagnostic_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 50}")
    print(f"Results saved to: {results_path}")
    print(f"Audio files saved to: {OUTPUT_DIR}")
    
    # Summary
    print(f"\n=== SUMMARY ===")
    if ref_info:
        dur = ref_info.get("duration", 0)
        if dur < 1 or dur > 30:
            print(f"REFERENCE AUDIO: Problematic duration ({dur}s)")
        else:
            print(f"REFERENCE AUDIO: OK ({dur}s)")
    
    # Check consistency
    if "consistency" in all_results:
        sizes = [r.get("size_kb", 0) for r in all_results["consistency"] if "size_kb" in r]
        if sizes:
            min_size = min(sizes)
            max_size = max(sizes)
            variance = max_size - min_size
            print(f"CONSISTENCY: Min={min_size}KB, Max={max_size}KB, Variance={variance}KB")
            if variance > 50:
                print("  WARNING: High variance - API is non-deterministic")
            else:
                print("  OK: Consistent output sizes")


if __name__ == "__main__":
    main()