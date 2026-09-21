"""
Luna JARVIS — Session 34: E2E Pipeline Test with Edge TTS
Tests the full voice pipeline: Edge TTS → audio → ASR → verify

Expected results based on Session 33 findings:
- Edge TTS with es-CL-CatalinaNeural should produce clear audio
- ASR should correctly transcribe the audio
- "Dekov" should be recognized (or fixed by respelling)
"""

import sys
import os
import json
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from voice.tts import TTSEngine
from voice.text_processor import fix_asr_names, optimize_for_voice_clone
from brain.mimo_client import get_client


def test_edge_tts_e2e():
    """Full E2E test: Edge TTS → audio file → ASR → verify transcription."""
    
    # Test cases with expected transcriptions
    test_cases = [
        {
            "id": "greeting",
            "text": "Hola Dekov, buenas noches. Soy Luna, tu asistente personal.",
            "expected_keywords": ["hola", "buenas", "noches", "luna", "asistente"],
            "expected_name": "Dekov",
        },
        {
            "id": "system_info",
            "text": "Tu CPU está al 45 por ciento y la RAM al 72 por ciento.",
            "expected_keywords": ["cpu", "cuarenta", "cincuenta", "por ciento", "ram"],
            "expected_name": None,
        },
        {
            "id": "natural_conversation",
            "text": "¿Cómo estai hoy? Espero que hayas tenido un buen día.",
            "expected_keywords": ["como", "espero", "buen", "dia"],
            "expected_name": None,
        },
        {
            "id": "technical",
            "text": "Abrí VS Code y revisé el archivo main punto pi. Todo funciona bien.",
            "expected_keywords": ["code", "archivo", "funciona"],
            "expected_name": None,
        },
        {
            "id": "chilean_slang",
            "text": "Wena po Dekov, cachai que el servicio está corriendo bien.",
            "expected_keywords": ["wena", "servicio", "corriendo", "bien"],
            "expected_name": "Dekov",
        },
    ]
    
    # Initialize
    client = get_client()
    tts = TTSEngine(
        client,
        default_tts="edge",
        edge_voice="es-CL-CatalinaNeural"
    )
    
    results = []
    output_dir = Path(__file__).parent / "experiments" / "session34_e2e"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Luna JARVIS — Session 34: E2E Pipeline Test")
    print("=" * 60)
    
    for tc in test_cases:
        print(f"\n--- Test: {tc['id']} ---")
        print(f"Input: {tc['text']}")
        
        # Step 1: Generate audio with Edge TTS
        t0 = time.time()
        audio = tts.speak(tc["text"], use_edge=True)
        tts_time = time.time() - t0
        
        if not audio:
            print(f"❌ TTS failed — no audio generated")
            results.append({"id": tc["id"], "tts": "FAIL", "asr": "SKIP", "match": False})
            continue
        
        # Save audio
        audio_path = output_dir / f"{tc['id']}.wav"
        with open(audio_path, "wb") as f:
            f.write(audio)
        
        print(f"✅ TTS: {len(audio)} bytes, {tts_time:.1f}s")
        
        # Step 2: Transcribe with ASR
        try:
            t0 = time.time()
            transcript = client.asr(str(audio_path))
            asr_time = time.time() - t0
            print(f"ASR raw: '{transcript}' ({asr_time:.1f}s)")
            
            # Step 3: Apply respelling fix
            fixed = fix_asr_names(transcript)
            print(f"ASR fixed: '{fixed}'")
            
            # Step 4: Check keywords
            transcript_lower = fixed.lower()
            matched_keywords = [kw for kw in tc["expected_keywords"] if kw in transcript_lower]
            keyword_score = len(matched_keywords) / len(tc["expected_keywords"]) * 100
            
            # Check name
            name_ok = True
            if tc["expected_name"]:
                name_ok = tc["expected_name"].lower() in transcript_lower
            
            match = keyword_score >= 50 and name_ok
            
            print(f"Keywords: {matched_keywords}/{tc['expected_keywords']} ({keyword_score:.0f}%)")
            if tc["expected_name"]:
                print(f"Name '{tc['expected_name']}': {'✅' if name_ok else '❌'}")
            print(f"Overall: {'✅ PASS' if match else '❌ FAIL'}")
            
            results.append({
                "id": tc["id"],
                "input": tc["text"],
                "asr_raw": transcript,
                "asr_fixed": fixed,
                "keywords_pct": keyword_score,
                "name_ok": name_ok,
                "tts_bytes": len(audio),
                "tts_time": tts_time,
                "asr_time": asr_time,
                "pass": match,
            })
            
        except Exception as e:
            print(f"❌ ASR error: {e}")
            results.append({"id": tc["id"], "tts": "OK", "asr": f"ERROR: {e}", "pass": False})
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for r in results if r.get("pass"))
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    for r in results:
        status = "✅" if r.get("pass") else "❌"
        print(f"  {status} {r['id']}: keywords={r.get('keywords_pct', 0):.0f}%")
    
    # Save results
    results_path = output_dir / "results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved: {results_path}")
    
    return results


if __name__ == "__main__":
    test_edge_tts_e2e()
