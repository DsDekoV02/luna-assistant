"""
Luna JARVIS - Voice Clone V3 Comparison Test
Generates audio with V3 text processor and compares with V2 baseline.
Uses MiMo API to generate real voice clone audio.

Requires: MIMO_API_KEY in environment.
"""

import os
import sys
import time
import json
import hashlib
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.text_processor import optimize_for_voice_clone
from brain.mimo_client import MiMoClient


# Test phrases covering various text processor features
V3_TEST_CASES = [
    {
        "id": "basic_greeting",
        "input": "¡Hola Nicolás! ¿Cómo estás? Soy Luna, tu asistente personal.",
        "description": "Saludo básico con acentos",
    },
    {
        "id": "numbers_percentages",
        "input": "Tienes 3 mensajes nuevos. La CPU está al 45% y la RAM al 72%.",
        "description": "Números y porcentajes",
    },
    {
        "id": "tech_terms",
        "input": "Tu PC tiene 16GB de RAM, un procesador Intel i7 y una GPU RTX 3080.",
        "description": "Términos técnicos y unidades",
    },
    {
        "id": "file_extensions",
        "input": "Abre VS Code y revisa el archivo main.py. Hay un bug en la línea 42.",
        "description": "Extensiones de archivo y términos de programación",
    },
    {
        "id": "abbreviations",
        "input": "El Dr. García dijo que el Ing. Torres llegará a las 14:30.",
        "description": "Abreviaciones y formato de hora",
    },
    {
        "id": "symbols_and_urls",
        "input": "El precio es $5.000 & el descuento es del 15%. Visita https://ejemplo.com/info.",
        "description": "Símbolos, URLs y protección de contenido",
    },
    {
        "id": "complex_conversation",
        "input": "Bueno, entonces te explico: la API del servidor devuelve un error 404. ¿Quieres que revise el archivo config.json?",
        "description": "Conversación compleja con pausas naturales",
    },
    {
        "id": "decimal_numbers",
        "input": "La temperatura es de 23.5°C y la velocidad de 3.14 metros por segundo.",
        "description": "Números decimales y unidades",
    },
    {
        "id": "english_words",
        "input": "OK, voy a hacer click en el browser y hacer download del archivo.",
        "description": "Palabras en inglés comunes en tech",
    },
    {
        "id": "repeated_chars",
        "input": "Noooo, no quiero que se borre el archivo!!!!",
        "description": "Caracteres repetidos y exclamaciones",
    },
]


def generate_audio(client: MiMoClient, text: str, voice_ref_path: str, output_path: str):
    """Generate voice clone audio and save to file."""
    audio = client.voice_clone(text, voice_ref_path)
    with open(output_path, "wb") as f:
        f.write(audio)
    return len(audio)


def run_comparison_test():
    """Run V3 text processor comparison test."""
    api_key = os.environ.get("MIMO_API_KEY")
    if not api_key:
        print("ERROR: MIMO_API_KEY not set. Skipping voice clone test.")
        return

    client = MiMoClient(api_key=api_key)
    voice_ref = str(Path(__file__).parent.parent.parent / "experiments" / "luna_voz_v5b_kohana_fina.wav")

    if not Path(voice_ref).exists():
        print(f"ERROR: Voice reference not found: {voice_ref}")
        return

    # Output directory
    output_dir = Path(__file__).parent.parent.parent / "experiments" / "clone_v3_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    print("=" * 60)
    print("LUNA JARVIS - Voice Clone V3 Comparison Test")
    print(f"Date: {datetime.now().isoformat()}")
    print(f"Voice reference: {Path(voice_ref).name}")
    print("=" * 60)

    for tc in V3_TEST_CASES:
        test_id = tc["id"]
        original = tc["input"]
        optimized = optimize_for_voice_clone(original)

        print(f"\n--- {test_id}: {tc['description']} ---")
        print(f"  Original:   {original}")
        print(f"  Optimized:  {optimized}")

        # Generate audio with optimized text
        output_path = str(output_dir / f"v3_{test_id}.wav")
        try:
            t0 = time.time()
            size = generate_audio(client, optimized, voice_ref, output_path)
            elapsed = time.time() - t0

            result = {
                "id": test_id,
                "original": original,
                "optimized": optimized,
                "audio_file": output_path,
                "audio_size_kb": size / 1024,
                "generation_time_s": round(elapsed, 2),
                "status": "success",
            }
            print(f"  Audio: {size/1024:.1f} KB in {elapsed:.1f}s → {output_path}")

        except Exception as e:
            result = {
                "id": test_id,
                "original": original,
                "optimized": optimized,
                "error": str(e),
                "status": "error",
            }
            print(f"  ERROR: {e}")

        results.append(result)
        time.sleep(0.5)  # Rate limit

    # Save results
    results_file = str(output_dir / "v3_comparison_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "processor_version": "V4",
            "test_cases": len(results),
            "successes": sum(1 for r in results if r["status"] == "success"),
            "results": results,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"Results saved to: {results_file}")
    successes = sum(1 for r in results if r["status"] == "success")
    print(f"Success: {successes}/{len(results)}")
    print("=" * 60)


if __name__ == "__main__":
    run_comparison_test()
