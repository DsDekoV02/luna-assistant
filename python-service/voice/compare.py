#!/usr/bin/env python3
"""
Luna JARVIS - Voice Comparison Tool
Generates the same text with all TTS backends for quality comparison.
Outputs WAV files + metadata JSON for side-by-side evaluation.
"""

import os
import sys
import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.mimo_client import get_client
from voice.tts import TTSEngine
from voice.text_processor import optimize_for_voice_clone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("voice_compare")

# ── Test Phrases ──────────────────────────────────────────────────

TEST_PHRASES = [
    {
        "id": "greeting",
        "text": "¡Hola Nicolas! Soy Luna, tu asistente. ¿En qué puedo ayudarte hoy?",
        "category": "saludo",
    },
    {
        "id": "technical",
        "text": "El motor de emociones detectó que estás un poco frustrado. ¿Quieres que te ayude con el código?",
        "category": "técnico",
    },
    {
        "id": "chilean",
        "text": "Wena po compadre, ¿cómo andai? Voy a revisar el proyecto de Luna JARVIS pa' ver cómo va.",
        "category": "chileno",
    },
    {
        "id": "long",
        "text": "Según los datos del sistema, tienes 47 por ciento de RAM en uso, el disco C tiene 120 gigabytes libres, y la batería está al 85 por ciento conectada a corriente.",
        "category": "datos",
    },
    {
        "id": "emotional",
        "text": "Me alegra mucho que estés trabajando en este proyecto juntos. Cada día mejoramos más, y eso me hace sentir... bueno, lo más cercano a feliz que una AI puede sentir.",
        "category": "emocional",
    },
]

# ── Voice Comparison Engine ───────────────────────────────────────

class VoiceComparator:
    """Compare all TTS backends on the same test phrases."""

    BACKENDS = ["edge", "clone", "design", "standard"]

    def __init__(self, output_dir: str = None):
        self.client = get_client()
        config_path = Path(__file__).parent.parent / "config.yaml"
        import yaml
        config = {}
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}

        voice_ref = config.get("voice_ref_path", "../experiments/luna_voz_v5b_kohana_fina.wav")
        voice_ref_abs = str(Path(__file__).parent.parent / voice_ref)
        edge_voice = config.get("voice", {}).get("edge_voice", "es-CL-CatalinaNeural")

        self.tts = TTSEngine(
            self.client,
            voice_ref_path=voice_ref_abs,
            voice_design_profile=config.get("voice_design_profile", "anime_es"),
            default_tts="edge",
            edge_voice=edge_voice,
        )

        if output_dir is None:
            output_dir = str(Path(__file__).parent.parent / "voice_diagnostics" / "comparisons")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_comparison(self, backends: list = None, phrases: list = None) -> dict:
        """Run voice comparison across backends and phrases.

        Returns dict with results metadata.
        """
        if backends is None:
            backends = self.BACKENDS
        if phrases is None:
            phrases = TEST_PHRASES

        results = {
            "generated_at": datetime.now().isoformat(),
            "backends": {},
            "phrases": [],
            "summary": {},
        }

        for phrase in phrases:
            phrase_result = {
                "id": phrase["id"],
                "text": phrase["text"],
                "category": phrase["category"],
                "backends": {},
            }

            for backend in backends:
                try:
                    logger.info(f"  [{backend}] Generating: {phrase['id']}...")
                    start = time.time()

                    if backend == "edge":
                        audio = self.tts.speak(phrase["text"], use_edge=True)
                    elif backend == "clone":
                        audio = self.tts.speak(phrase["text"], use_clone=True, use_edge=False)
                    elif backend == "design":
                        audio = self.tts.speak(phrase["text"], use_design=True, use_edge=False)
                    elif backend == "standard":
                        audio = self.tts.speak(phrase["text"], use_clone=False, use_design=False, use_edge=False)
                    else:
                        continue

                    elapsed = time.time() - start

                    if audio:
                        # Save WAV
                        filename = f"{phrase['id']}_{backend}.wav"
                        filepath = self.output_dir / filename
                        with open(filepath, "wb") as f:
                            f.write(audio)

                        phrase_result["backends"][backend] = {
                            "file": str(filepath),
                            "filename": filename,
                            "size_bytes": len(audio),
                            "duration_estimate_s": round(len(audio) / 32000, 2),  # rough estimate
                            "generation_time_s": round(elapsed, 2),
                            "status": "ok",
                        }
                        logger.info(f"    ✓ {filename} ({len(audio)} bytes, {elapsed:.1f}s)")
                    else:
                        phrase_result["backends"][backend] = {
                            "status": "failed",
                            "error": "No audio generated",
                        }
                        logger.warning(f"    ✗ No audio for {backend}")

                except Exception as e:
                    phrase_result["backends"][backend] = {
                        "status": "error",
                        "error": str(e),
                    }
                    logger.error(f"    ✗ {backend} error: {e}")

            results["phrases"].append(phrase_result)

        # Build summary
        for backend in backends:
            ok_count = sum(
                1 for p in results["phrases"]
                if p["backends"].get(backend, {}).get("status") == "ok"
            )
            total_time = sum(
                p["backends"].get(backend, {}).get("generation_time_s", 0)
                for p in results["phrases"]
                if p["backends"].get(backend, {}).get("status") == "ok"
            )
            total_size = sum(
                p["backends"].get(backend, {}).get("size_bytes", 0)
                for p in results["phrases"]
                if p["backends"].get(backend, {}).get("status") == "ok"
            )
            results["summary"][backend] = {
                "success": ok_count,
                "total": len(phrases),
                "success_rate": f"{ok_count}/{len(phrases)}",
                "avg_generation_time_s": round(total_time / max(ok_count, 1), 2),
                "avg_file_size_bytes": round(total_size / max(ok_count, 1)),
                "total_size_bytes": total_size,
            }

        # Save results JSON
        results_path = self.output_dir / "comparison_results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"\nResults saved: {results_path}")

        return results

    def print_summary(self, results: dict):
        """Print a human-readable summary."""
        print("\n" + "=" * 60)
        print("VOICE COMPARISON SUMMARY")
        print("=" * 60)
        print(f"Generated: {results['generated_at']}")
        print(f"Phrases tested: {len(results['phrases'])}")
        print()

        for backend, stats in results["summary"].items():
            status = "✓" if stats["success"] == stats["total"] else "⚠"
            print(f"{status} {backend:10s} | {stats['success_rate']} ok | "
                  f"avg {stats['avg_generation_time_s']:.1f}s | "
                  f"avg {stats['avg_file_size_bytes'] / 1024:.0f}KB")

        print()
        print("Files saved in:", self.output_dir)
        print("\nPara comparar:")
        print("  1. Abre los WAV en tu reproductor de audio")
        print("  2. Compara naturalidad, pronunciación chilena, y expresividad")
        print("  3. Elige tu backend favorito en config.yaml → voice.default_tts")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Luna Voice Comparison Tool")
    parser.add_argument("--backends", nargs="+", default=None,
                        choices=["edge", "clone", "design", "standard"],
                        help="Backends to test (default: all)")
    parser.add_argument("--output", default=None, help="Output directory")
    args = parser.parse_args()

    comparator = VoiceComparator(output_dir=args.output)
    results = comparator.run_comparison(backends=args.backends)
    comparator.print_summary(results)


if __name__ == "__main__":
    main()
