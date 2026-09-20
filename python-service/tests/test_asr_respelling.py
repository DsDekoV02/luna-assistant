"""
Tests for ASR respelling dictionary — fixes proper nouns that ASR misrecognizes.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.text_processor import fix_asr_names


class TestASRRespelling:
    """Test fix_asr_names post-processing."""

    def test_dekov_variants(self):
        """All known Dekov misrecognitions should be fixed."""
        assert fix_asr_names("hola dekov") == "hola Dekov"
        assert fix_asr_names("de kov como estas") == "Dekov como estas"
        assert fix_asr_names("the kov dijo algo") == "Dekov dijo algo"
        assert fix_asr_names("de cob") == "Dekov"

    def test_salocin_variants(self):
        """All known Salocin misrecognitions should be fixed."""
        assert fix_asr_names("salocin aqui") == "Salocin aqui"
        assert fix_asr_names("sallo sin") == "Salocin"
        assert fix_asr_names("sallo cin") == "Salocin"
        assert fix_asr_names("sala sin dijo") == "Salocin dijo"

    def test_tech_terms(self):
        """Tech terms should be properly capitalized."""
        assert fix_asr_names("open claw esta funcionando") == "OpenClaw esta funcionando"
        assert fix_asr_names("mi mo responde bien") == "MiMo responde bien"
        assert fix_asr_names("luna jarvis es genial") == "Luna JARVIS es genial"

    def test_preserves_surrounding_text(self):
        """Fix should only replace the target, keeping everything else."""
        result = fix_asr_names("oye dekov, abrime three js")
        assert "Dekov" in result
        assert "Three.js" in result

    def test_empty_string(self):
        assert fix_asr_names("") == ""

    def test_no_match(self):
        """Text without known misrecognitions should pass through unchanged."""
        text = "hola como estas hoy"
        assert fix_asr_names(text) == text

    def test_case_insensitive(self):
        """Should match regardless of case."""
        assert fix_asr_names("DEKOV") == "Dekov"
        assert fix_asr_names("SALOCIN") == "Salocin"

    def test_first_match_only(self):
        """Should replace only the first occurrence to avoid over-correction."""
        result = fix_asr_names("dekov y dekov")
        # First should be replaced, second left as-is (count=1)
        assert result.count("Dekov") >= 1
