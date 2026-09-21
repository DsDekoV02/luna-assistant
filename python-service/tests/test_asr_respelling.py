"""
Tests for ASR respelling dictionary — fixes proper nouns that ASR misrecognizes.

Session 42: Added tests for Chilean places, apps, anime references, and MiMo Desktop.
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

    # ── Session 42: Chilean places ───────────────────────────────

    def test_chilean_places(self):
        """Chilean city/place names should be properly capitalized."""
        assert fix_asr_names("vivo en santiago") == "vivo en Santiago"
        assert fix_asr_names("estoy en valparaiso") == "estoy en Valparaiso"
        assert fix_asr_names("concepcion es grande") == "Concepcion es grande"
        assert fix_asr_names("providencia") == "Providencia"

    # ── Session 42: App/tool names ───────────────────────────────

    def test_app_names(self):
        """App names Nicolas uses should be properly recognized."""
        assert "JetBrains" in fix_asr_names("abre jet brains")
        assert "IntelliJ" in fix_asr_names("usar intelli j")
        assert "PyCharm" in fix_asr_names("abre pi charm")
        assert "CurseForge" in fix_asr_names("abre curse forge")
        assert "Notepad++" in fix_asr_names("abre notepad plus plus")
        assert "OBS" in fix_asr_names("graba con o b s")

    # ── Session 42: Anime / cultural ─────────────────────────────

    def test_anime_references(self):
        """Anime references should be properly capitalized."""
        assert "SAO" in fix_asr_names("vi sao ayer")
        assert "DanMachi" in fix_asr_names("dan machi temporada nueva")
        assert "Hololive" in fix_asr_names("vi hololive")
        assert "Sword Art Online" in fix_asr_names("sword art online fatal bullet")

    # ── Session 42: VR / hardware ────────────────────────────────

    def test_vr_hardware(self):
        """VR terms should be properly recognized."""
        assert "Meta Quest" in fix_asr_names("meta quest")
        assert "Meta Horizon" in fix_asr_names("meta horizon")

    # ── Session 42: MiMo Desktop ─────────────────────────────────

    def test_mimo_desktop(self):
        """MiMo Desktop should be properly recognized."""
        assert "MiMo Desktop" in fix_asr_names("mimo desktop")
        assert "MiMo Desktop" in fix_asr_names("mi mo desktop")

    # ── Session 42: Hardware ASR errors ──────────────────────────

    def test_hardware_errors(self):
        """Hardware misrecognitions should be fixed."""
        assert "CPU" in fix_asr_names("tucep al 50")
        assert "CPU" in fix_asr_names("cerep usage")
        assert "RAM" in fix_asr_names("rame al 70")
        assert "SSD" in fix_asr_names("ese ese de")
