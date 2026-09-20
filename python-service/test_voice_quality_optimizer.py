#!/usr/bin/env python3
"""
Voice Clone Quality Optimizer
Prueba diferentes configuraciones para encontrar la mejor calidad de voice clone.
"""

import os
import sys
import json
import time
import base64
import wave
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.mimo_client import MiMoClient
from voice.text_processor import optimize_for_voice_clone

EXPERIMENTS_DIR = Path(__file__).parent.parent / "experiments"
REFERENCE_AUDIO = EXPERIMENTS_DIR / "luna_voz_v5b_kohana_fina.wav"
OUTPUT_DIR = EXPERIMENTS_DIR / "voice_quality_optimizer"
OUTPUT_DIR.mkdir(exist_ok=True)


def get_audio_duration(filepath):
    """Get WAV audio duration in seconds."""
    try:
        with wave.open(str(filepath), 'rb') as wf:
            return wf.getnframes() / wf.getframerate()
    except:
        return 0


def test_with_different_texts(client, ref_path):
    """Test voice clone with different text styles."""
    print("\n=== TEST 1: Different Text Styles ===")
    
    tests = [
        # Simple, natural
        ("simple", "Hola Dekov, como estas hoy?"),
        # Conversational
        ("conversational", "Buenos dias Dekov, espero que tengas un excelente dia. En que puedo ayudarte?"),
        # Emotional - happy
        ("happy", "Que bueno verte Dekov! Me alegra mucho que hayas venido. Estoy feliz de ayudarte."),
        # Emotional - calm
        ("calm", "Tranquilo Dekov, todo va a estar bien. Voy a revisar todo con calma."),
        # Technical
        ("technical", "El sistema esta funcionando correctamente. La CPU esta al 45 por ciento y la memoria al 60 por ciento."),
        # Storytelling
        ("storytelling", "Habia una vez una luna que brillaba en el cielo nocturno. Cada noche observaba a las estrellas y sonreia."),
        # Mixed
        ("mixed", "Hola Dekov! Soy Luna, tu asistente. Hoy el clima esta despejado con 22 grados. Que te gustaria hacer?"),
    ]
    
    results = []
    for label, text in tests:
        processed = optimize_for_voice_clone(text)
        try:
            audio = client.voice_clone(processed, str(ref_path))
            size_kb = len(audio) / 1024
            filename = f"style_{label}.wav"
            filepath = OUTPUT_DIR / filename
            with open(filepath, "wb") as f:
                f.write(audio)
            results.append({"style": label, "text": text, "size_kb": round(size_kb, 1), "ok": size_kb > 50})
            print(f"  {label}: {size_kb:.1f} KB - {'OK' if size_kb > 50 else 'SUSPICIOUS'}")
            time.sleep(1)
        except Exception as e:
            print(f"  {label}: ERROR - {e}")
            results.append({"style": label, "error": str(e)})
    
    return results


def test_with_different_references(client):
    """Test voice clone with different reference audio files."""
    print("\n=== TEST 2: Different Reference Audio ===")
    
    ref_files = [
        ("kohana_fina", "luna_voz_v5b_kohana_fina.wav"),
        ("clone_test_1", "luna_clone_test_1.wav"),
        ("clone_test_4", "luna_clone_test_4.wav"),
        ("v6_test1", "luna_clone_v6_test1.wav"),
        ("session23_1", "session23_voice_test_1.wav"),
    ]
    
    test_text = optimize_for_voice_clone("Hola Dekov, como estas hoy?")
    results = []
    
    for label, filename in ref_files:
        ref_path = EXPERIMENTS_DIR / filename
        if not ref_path.exists():
            print(f"  {label}: FILE NOT FOUND")
            continue
        
        duration = get_audio_duration(ref_path)
        try:
            audio = client.voice_clone(test_text, str(ref_path))
            size_kb = len(audio) / 1024
            output_file = OUTPUT_DIR / f"ref_{label}.wav"
            with open(output_file, "wb") as f:
                f.write(audio)
            results.append({"ref": label, "duration_s": round(duration, 2), "size_kb": round(size_kb, 1), "ok": size_kb > 50})
            print(f"  {label} ({duration:.1f}s): {size_kb:.1f} KB - {'OK' if size_kb > 50 else 'SUSPICIOUS'}")
            time.sleep(1)
        except Exception as e:
            print(f"  {label}: ERROR - {e}")
            results.append({"ref": label, "error": str(e)})
    
    return results


def test_with_punctuation_variations(client, ref_path):
    """Test voice clone with different punctuation styles."""
    print("\n=== TEST 3: Punctuation Variations ===")
    
    base_text = "Hola Dekov, como estas hoy"
    
    tests = [
        ("no_punct", base_text),
        ("period", base_text + "."),
        ("question", base_text + "?"),
        ("exclamation", base_text + "!"),
        ("ellipsis", base_text + "..."),
        ("comma_pause", "Hola Dekov, como estas, hoy?"),
        ("natural_pause", "Hola Dekov... como estas hoy?"),
    ]
    
    results = []
    for label, text in tests:
        try:
            audio = client.voice_clone(text, str(ref_path))
            size_kb = len(audio) / 1024
            filename = f"punct_{label}.wav"
            filepath = OUTPUT_DIR / filename
            with open(filepath, "wb") as f:
                f.write(audio)
            results.append({"punct": label, "text": text, "size_kb": round(size_kb, 1)})
            print(f"  {label}: {size_kb:.1f} KB - '{text}'")
            time.sleep(1)
        except Exception as e:
            print(f"  {label}: ERROR - {e}")
    
    return results


def test_with_length_variations(client, ref_path):
    """Test optimal text length for voice clone."""
    print("\n=== TEST 4: Optimal Text Length ===")
    
    tests = [
        ("very_short", "Hola Dekov"),
        ("short", "Hola Dekov, como estas?"),
        ("medium", "Hola Dekov, como estas hoy? En que puedo ayudarte?"),
        ("long", "Hola Dekov, como estas hoy? En que puedo ayudarte? Quiero que sepas que estoy aqui para lo que necesites."),
        ("very_long", "Hola Dekov, como estas hoy? Quiero que sepas que estoy aqui para lo que necesites. Puedo ayudarte con el codigo, revisar el sistema, o simplemente conversar. Que te gustaria hacer?"),
    ]
    
    results = []
    for label, text in tests:
        words = len(text.split())
        try:
            audio = client.voice_clone(text, str(ref_path))
            size_kb = len(audio) / 1024
            filename = f"length_{label}.wav"
            filepath = OUTPUT_DIR / filename
            with open(filepath, "wb") as f:
                f.write(audio)
            results.append({"length": label, "words": words, "size_kb": round(size_kb, 1)})
            print(f"  {label} ({words} words): {size_kb:.1f} KB")
            time.sleep(1)
        except Exception as e:
            print(f"  {label}: ERROR - {e}")
    
    return results


def analyze_results(style_results, ref_results, punct_results, length_results):
    """Analyze all test results and provide recommendations."""
    print("\n" + "=" * 60)
    print("ANALYSIS & RECOMMENDATIONS")
    print("=" * 60)
    
    # Best style
    if style_results:
        valid_styles = [r for r in style_results if r.get("ok")]
        if valid_styles:
            best_style = max(valid_styles, key=lambda x: x["size_kb"])
            print(f"\nBest text style: {best_style['style']} ({best_style['size_kb']} KB)")
    
    # Best reference
    if ref_results:
        valid_refs = [r for r in ref_results if r.get("ok")]
        if valid_refs:
            best_ref = max(valid_refs, key=lambda x: x["size_kb"])
            print(f"Best reference audio: {best_ref['ref']} ({best_ref['duration_s']}s, {best_ref['size_kb']} KB)")
    
    # Best punctuation
    if punct_results:
        best_punct = max(punct_results, key=lambda x: x["size_kb"])
        print(f"Best punctuation style: {best_punct['punct']} ({best_punct['size_kb']} KB)")
    
    # Best length
    if length_results:
        valid_lengths = [r for r in length_results if r.get("size_kb", 0) > 50]
        if valid_lengths:
            best_length = max(valid_lengths, key=lambda x: x["size_kb"])
            print(f"Optimal text length: {best_length['length']} ({best_length['words']} words, {best_length['size_kb']} KB)")


def main():
    print("Voice Clone Quality Optimizer")
    print("=" * 60)
    
    client = MiMoClient()
    
    # Run all tests
    style_results = test_with_different_texts(client, REFERENCE_AUDIO)
    ref_results = test_with_different_references(client)
    punct_results = test_with_punctuation_variations(client, REFERENCE_AUDIO)
    length_results = test_with_length_variations(client, REFERENCE_AUDIO)
    
    # Analyze
    analyze_results(style_results, ref_results, punct_results, length_results)
    
    # Save all results
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "style_tests": style_results,
        "reference_tests": ref_results,
        "punctuation_tests": punct_results,
        "length_tests": length_results
    }
    
    results_path = OUTPUT_DIR / "optimizer_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {results_path}")
    print(f"Audio files saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()