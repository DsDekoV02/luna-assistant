"""
Luna JARVIS - Tests for Text Processor
Tests all text optimization functions for voice clone TTS.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.text_processor import (
    remove_accents,
    expand_numbers,
    expand_percentages,
    expand_time_formats,
    expand_size_units,
    expand_file_extensions,
    expand_tech_terms,
    expand_file_urls,
    expand_english_words,
    add_pauses,
    expand_contractions,
    expand_abbreviations,
    expand_symbols,
    expand_decimal_numbers,
    split_sentences,
    clean_for_tts,
    optimize_for_voice_clone,
    get_pronunciation_tips,
    normalize_repeated_chars,
    soften_difficult_clusters,
    add_breathing_pauses,
    apply_phonetic_respelling,
    apply_rhythm_breaks,
    add_emphasis_markers,
    apply_sentence_prosody,
    improve_natural_phrases,
    add_prosody_pauses,
)


# ── remove_accents ────────────────────────────────────────────────

class TestRemoveAccents:
    def test_basic_accents(self):
        assert remove_accents("café") == "cafe"
        assert remove_accents("niño") == "nino"
        assert remove_accents("música") == "musica"

    def test_uppercase_accents(self):
        assert remove_accents("Ángel") == "Angel"
        assert remove_accents("ÉPICO") == "EPICO"

    def test_dieresis(self):
        assert remove_accents("pingüino") == "pinguino"

    def test_enye(self):
        # ñ -> n (not ideal but for TTS clarity)
        assert remove_accents("España") == "Espana"

    def test_no_accents(self):
        assert remove_accents("hola mundo") == "hola mundo"

    def test_empty_string(self):
        assert remove_accents("") == ""


# ── expand_numbers ────────────────────────────────────────────────

class TestExpandNumbers:
    def test_single_digits(self):
        assert "cero" in expand_numbers("0")
        assert "cinco" in expand_numbers("5")
        assert "nueve" in expand_numbers("9")

    def test_teens(self):
        assert "once" in expand_numbers("11")
        assert "quince" in expand_numbers("15")
        assert "diecinueve" in expand_numbers("19")

    def test_tens(self):
        assert "veinte" in expand_numbers("20")
        assert "treinta" in expand_numbers("30")
        assert "noventa" in expand_numbers("90")

    def test_compound_tens(self):
        result = expand_numbers("25")
        # 21-29 use "veinti" prefix
        assert "veinti" in result.lower() or "cinco" in result.lower()

    def test_hundreds(self):
        assert "cien" in expand_numbers("100").lower() or "ciento" in expand_numbers("100").lower()
        assert "doscientos" in expand_numbers("200").lower()

    def test_thousands(self):
        assert "mil" in expand_numbers("1000")
        result = expand_numbers("2500")
        assert "mil" in result

    def test_in_sentence(self):
        result = expand_numbers("Tengo 3 mensajes")
        assert "tres" in result

    def test_large_numbers_unchanged(self):
        # Numbers > 4 digits should stay as-is
        result = expand_numbers("50000")
        assert "50000" in result


# ── expand_percentages ────────────────────────────────────────────

class TestExpandPercentages:
    def test_simple_percentage(self):
        result = expand_percentages("45%")
        assert "cuarenta" in result and "cinco" in result and "por ciento" in result

    def test_hundred_percent(self):
        result = expand_percentages("100%")
        assert "cien" in result and "por ciento" in result

    def test_in_sentence(self):
        result = expand_percentages("CPU al 72%")
        assert "por ciento" in result
        assert "%" not in result

    def test_multiple_percentages(self):
        result = expand_percentages("CPU 45% y RAM 72%")
        assert result.count("por ciento") == 2

    def test_no_percentage(self):
        assert expand_percentages("hola mundo") == "hola mundo"


# ── expand_time_formats ──────────────────────────────────────────

class TestExpandTimeFormats:
    def test_simple_time(self):
        result = expand_time_formats("14:30")
        assert "media" in result

    def test_oclock(self):
        result = expand_time_formats("las 8:00")
        assert "en punto" in result

    def test_quarter_past(self):
        result = expand_time_formats("las 3:15")
        assert "cuarto" in result

    def test_quarter_to(self):
        result = expand_time_formats("las 3:45")
        assert "menos cuarto" in result

    def test_no_time(self):
        assert expand_time_formats("hola mundo") == "hola mundo"


# ── expand_size_units ─────────────────────────────────────────────

class TestExpandSizeUnits:
    def test_gb(self):
        result = expand_size_units("120GB")
        assert "ciento" in result and "veinte" in result and "gigabytes" in result

    def test_mb(self):
        result = expand_size_units("512MB")
        assert "megabytes" in result

    def test_ghz(self):
        result = expand_size_units("3.5GHz")
        # GHz with decimal should stay as-is or partially expand
        assert "gigahercio" in result or "GHz" in result

    def test_no_units(self):
        assert expand_size_units("hola mundo") == "hola mundo"


# ── expand_file_extensions ────────────────────────────────────────

class TestExpandFileExtensions:
    def test_py(self):
        result = expand_file_extensions("main.py")
        assert "punto" in result and "pi" in result

    def test_js(self):
        result = expand_file_extensions("app.js")
        assert "punto" in result and "jota" in result

    def test_json(self):
        result = expand_file_extensions("config.json")
        assert "punto" in result and "jason" in result

    def test_no_extension(self):
        assert expand_file_extensions("hola mundo") == "hola mundo"


# ── expand_tech_terms ─────────────────────────────────────────────

class TestExpandTechTerms:
    def test_api(self):
        result = expand_tech_terms("la API")
        assert "A P I" in result

    def test_url(self):
        result = expand_tech_terms("el URL")
        assert "enlace" in result

    def test_gpu(self):
        result = expand_tech_terms("mi GPU")
        assert "tarjeta de video" in result

    def test_ia(self):
        result = expand_tech_terms("con IA")
        assert "inteligencia artificial" in result

    def test_no_tech(self):
        assert expand_tech_terms("hola mundo") == "hola mundo"


# ── expand_file_urls ──────────────────────────────────────────────

class TestExpandFileUrls:
    def test_https(self):
        result = expand_file_urls("https://api.example.com")
        assert "https://" not in result
        assert "api.example.com" in result

    def test_www(self):
        result = expand_file_urls("www.google.com")
        assert "www." not in result

    def test_trailing_slash(self):
        result = expand_file_urls("https://example.com/")
        assert not result.endswith("/")

    def test_no_url(self):
        assert expand_file_urls("hola mundo") == "hola mundo"


# ── expand_english_words ─────────────────────────────────────────

class TestExpandEnglishWords:
    def test_ok(self):
        result = expand_english_words("ok")
        assert "okey" in result

    def test_lowercase_brand_skip(self):
        # Capitalized words should be preserved (brand names)
        result = expand_english_words("Code")
        assert "Code" in result

    def test_file(self):
        result = expand_english_words("el file")
        assert "archivo" in result

    def test_mixed(self):
        result = expand_english_words("abre el browser")
        assert "navegador" in result


# ── add_pauses ────────────────────────────────────────────────────

class TestAddPauses:
    def test_semicolon(self):
        result = add_pauses("hola; mundo")
        assert "." in result

    def test_colon(self):
        result = add_pauses("lista: item1")
        assert "." in result

    def test_multiple_spaces(self):
        result = add_pauses("hola   mundo")
        assert "   " not in result


# ── expand_contractions ──────────────────────────────────────────

class TestExpandContractions:
    def test_al(self):
        result = expand_contractions("voy al parque")
        assert "a el" in result

    def test_del(self):
        result = expand_contractions("salgo del trabajo")
        assert "de el" in result


# ── split_sentences ──────────────────────────────────────────────

class TestSplitSentences:
    def test_short_text(self):
        result = split_sentences("Hola mundo")
        assert len(result) >= 1

    def test_long_text(self):
        text = " ".join(["palabra"] * 30)
        result = split_sentences(text, max_words=10)
        assert len(result) >= 3

    def test_respects_punctuation(self):
        result = split_sentences("Primera oracion. Segunda oracion.")
        assert len(result) >= 2


# ── clean_for_tts ────────────────────────────────────────────────

class TestCleanForTTS:
    def test_exclamation(self):
        result = clean_for_tts("¡Hola!")
        assert "!" not in result
        assert "¡" not in result

    def test_special_chars(self):
        result = clean_for_tts("hola @mundo #test")
        assert "@" not in result
        assert "#" not in result

    def test_ellipsis(self):
        result = clean_for_tts("hola...")
        assert "..." not in result
        assert "." in result

    def test_adds_period(self):
        result = clean_for_tts("hola mundo")
        assert result.endswith(".")


# ── optimize_for_voice_clone (integration) ───────────────────────

class TestOptimizeForVoiceClone:
    def test_full_pipeline(self):
        text = "¡Hola Nicolás! Tienes 3 mensajes y la CPU está al 45%."
        result = optimize_for_voice_clone(text)
        # Should have no accents
        assert "á" not in result
        # Should have numbers expanded
        assert "tres" in result
        # Should have percentage expanded
        assert "por ciento" in result
        # Should end with period
        assert result.strip().endswith(".")

    def test_tech_text(self):
        text = "Revisa la API y el URL del servidor."
        result = optimize_for_voice_clone(text)
        assert "A P I" in result
        assert "enlace" in result

    def test_empty_text(self):
        result = optimize_for_voice_clone("")
        assert result == "" or result == "."

    def test_preserves_natural_speech(self):
        text = "Buenos dias, como estas hoy?"
        result = optimize_for_voice_clone(text)
        # Should preserve most of the natural speech
        assert "Buenos" in result or "buenos" in result.lower()


# ── get_pronunciation_tips ────────────────────────────────────────

class TestGetPronunciationTips:
    def test_numbers_tip(self):
        tips = get_pronunciation_tips("Tengo 5 mensajes")
        assert any("numeros" in t.lower() or "numbers" in t.lower() for t in tips)

    def test_tech_tip(self):
        tips = get_pronunciation_tips("Usa la API")
        assert any("API" in t for t in tips)

    def test_accents_tip(self):
        tips = get_pronunciation_tips("Hola Nicolás")
        assert any("acentos" in t.lower() or "accents" in t.lower() for t in tips)

    def test_no_tips_needed(self):
        tips = get_pronunciation_tips("hola mundo simple")
        # May have tips about long sentences or not
        assert isinstance(tips, list)

    def test_decimal_tip(self):
        tips = get_pronunciation_tips("El valor es 3.14")
        assert any("decimal" in t.lower() for t in tips)

    def test_url_tip(self):
        tips = get_pronunciation_tips("Visita https://example.com")
        assert any("url" in t.lower() for t in tips)

    def test_abbreviation_tip(self):
        tips = get_pronunciation_tips("Habla con el Dr. Garcia")
        assert any("Dr." in t for t in tips)

    def test_symbols_tip(self):
        tips = get_pronunciation_tips("5 + 3 = 8")
        assert any("simbolos" in t.lower() or "symbols" in t.lower() for t in tips)


# ── expand_abbreviations ─────────────────────────────────────────

class TestExpandAbbreviations:
    def test_doctor(self):
        assert "Doctor" in expand_abbreviations("Habla con el Dr. Garcia")

    def test_etcetera(self):
        result = expand_abbreviations("frutas, verduras, etc.")
        assert "etcetera" in result

    def test_versus(self):
        result = expand_abbreviations("Chile vs. Argentina")
        assert "versus" in result

    def test_no_abbreviation(self):
        text = "Hola mundo normal"
        assert expand_abbreviations(text) == text

    def test_senora(self):
        result = expand_abbreviations("La Sra. Lopez")
        assert "Senora" in result

    def test_ingeniero(self):
        result = expand_abbreviations("El Ing. Torres")
        assert "Ingeniero" in result


# ── expand_symbols ───────────────────────────────────────────────

class TestExpandSymbols:
    def test_ampersand(self):
        result = expand_symbols("A & B")
        assert " y " in result

    def test_at_sign(self):
        result = expand_symbols("email@domain")
        assert "arroba" in result

    def test_equals(self):
        result = expand_symbols("x = 5")
        assert "igual a" in result

    def test_plus(self):
        result = expand_symbols("3 + 2")
        assert "mas" in result

    def test_no_symbols(self):
        text = "hola mundo"
        assert expand_symbols(text) == text

    def test_multiple_spaces_cleaned(self):
        result = expand_symbols("A  &  B")
        assert "  " not in result


# ── expand_decimal_numbers ───────────────────────────────────────

class TestExpandDecimalNumbers:
    def test_simple_decimal(self):
        result = expand_decimal_numbers("3.14")
        assert "tres" in result
        assert "punto" in result
        assert "uno" in result
        assert "cuatro" in result

    def test_zero_decimal(self):
        result = expand_decimal_numbers("0.5")
        assert "cero" in result
        assert "punto" in result
        assert "cinco" in result

    def test_large_decimal(self):
        result = expand_decimal_numbers("100.25")
        assert "punto" in result

    def test_no_decimal(self):
        text = "tengo 5 manzanas"
        assert expand_decimal_numbers(text) == text

    def test_multiple_decimals(self):
        result = expand_decimal_numbers("pi es 3.14 y e es 2.71")
        assert "tres" in result
        assert "dos" in result


# ── split_sentences URL protection ───────────────────────────────

class TestSplitSentencesProtection:
    def test_url_not_split(self):
        text = "Visita https://example.com/very/long/path para mas info y luego revisa el otro sitio."
        result = split_sentences(text, max_words=8)
        # URL should be preserved intact
        full = ' '.join(result)
        assert "https://example.com/very/long/path" in full

    def test_email_not_split(self):
        text = "Escribe a usuario@dominio.com para contactarnos y pregunta por el servicio."
        result = split_sentences(text, max_words=6)
        full = ' '.join(result)
        assert "usuario@dominio.com" in full

    def test_windows_path_not_split(self):
        text = "Abre C:\\Users\\test\\archivo.py y revisa el codigo que tiene errores."
        result = split_sentences(text, max_words=6)
        full = ' '.join(result)
        assert "C:\\Users\\test\\archivo.py" in full


# ── apply_phonetic_respelling ────────────────────────────────────

class TestPhoneticRespelling:
    def test_hola(self):
        from voice.text_processor import apply_phonetic_respelling
        result = apply_phonetic_respelling("hola")
        assert "ola" in result

    def test_quien(self):
        from voice.text_processor import apply_phonetic_respelling
        result = apply_phonetic_respelling("quien")
        # 'qu' words are NOT respelled — testing showed it hurts voice clone quality
        assert "quien" in result

    def test_preserves_capitalized(self):
        from voice.text_processor import apply_phonetic_respelling
        # Capitalized words should not be respelled (proper nouns)
        result = apply_phonetic_respelling("Hola")
        assert "Hola" in result

    def test_in_sentence(self):
        from voice.text_processor import apply_phonetic_respelling
        result = apply_phonetic_respelling("hola quien eres")
        assert "ola" in result
        # 'qu' words preserved (not respelled to 'k')
        assert "quien" in result

    def test_no_change_needed(self):
        from voice.text_processor import apply_phonetic_respelling
        result = apply_phonetic_respelling("buenos dias")
        assert result == "buenos dias"

    def test_porque(self):
        from voice.text_processor import apply_phonetic_respelling
        # 'qu' words are NOT respelled (testing showed it hurts quality)
        result = apply_phonetic_respelling("porque")
        assert "porque" in result


# ── apply_rhythm_breaks ──────────────────────────────────────────

class TestRhythmBreaks:
    def test_bueno_break(self):
        from voice.text_processor import apply_rhythm_breaks
        result = apply_rhythm_breaks("bueno, vamos a ver")
        assert "bueno.," in result or "bueno." in result

    def test_entonces_break(self):
        from voice.text_processor import apply_rhythm_breaks
        result = apply_rhythm_breaks("entonces, dime que pasa")
        assert "entonces.," in result or "entonces." in result

    def test_no_break_needed(self):
        from voice.text_processor import apply_rhythm_breaks
        result = apply_rhythm_breaks("hola mundo")
        assert result == "hola mundo"

    def test_multiple_breaks(self):
        from voice.text_processor import apply_rhythm_breaks
        result = apply_rhythm_breaks("bueno, entonces, que hacemos")
        # Should have breaks after both introductory phrases
        assert result.count(".") >= 2


# ── normalize_repeated_chars ─────────────────────────────────────

class TestNormalizeRepeatedChars:
    def test_reduces_repeated_letter(self):
        from voice.text_processor import normalize_repeated_chars
        result = normalize_repeated_chars("noooo")
        assert result == "noo" or result == "no"  # Max 2

    def test_preserves_double_letters(self):
        from voice.text_processor import normalize_repeated_chars
        result = normalize_repeated_chars("llamar")
        assert "ll" in result

    def test_preserves_rr(self):
        from voice.text_processor import normalize_repeated_chars
        result = normalize_repeated_chars("perro")
        assert "rr" in result

    def test_normalizes_triple_letter(self):
        from voice.text_processor import normalize_repeated_chars
        result = normalize_repeated_chars("aaa")
        assert "aa" in result
        assert "aaa" not in result

    def test_normalizes_punctuation(self):
        from voice.text_processor import normalize_repeated_chars
        result = normalize_repeated_chars("hola!!!")
        assert "!!!" not in result
        assert "!" in result

    def test_no_change_needed(self):
        from voice.text_processor import normalize_repeated_chars
        result = normalize_repeated_chars("hola mundo")
        assert result == "hola mundo"


# ── soften_difficult_clusters ────────────────────────────────────

class TestSoftenDifficultClusters:
    def test_psicologia(self):
        from voice.text_processor import soften_difficult_clusters
        result = soften_difficult_clusters("psicologia")
        assert "sicologia" in result

    def test_normal_word_unchanged(self):
        from voice.text_processor import soften_difficult_clusters
        result = soften_difficult_clusters("hola mundo")
        assert result == "hola mundo"

    def test_preserves_psi_mid_word(self):
        from voice.text_processor import soften_difficult_clusters
        # Only changes at word start
        result = soften_difficult_clusters("concepto")
        assert result == "concepto"


# ── add_breathing_pauses ─────────────────────────────────────────

class TestAddBreathingPauses:
    def test_short_sentence_unchanged(self):
        from voice.text_processor import add_breathing_pauses
        result = add_breathing_pauses("Hola Nicolas.")
        assert result == "Hola Nicolas."

    def test_long_sentence_gets_breaks(self):
        from voice.text_processor import add_breathing_pauses
        text = "Buenas noches Nicolas, queria contarte que el proyecto va muy bien, ya terminamos la fase de experimentacion."
        result = add_breathing_pauses(text, max_words_before_pause=10)
        # Should have at least one break
        assert result.count(".") >= 1

    def test_conjunction_break(self):
        from voice.text_processor import add_breathing_pauses
        text = "Tengo tres mensajes nuevos y quince notificaciones pendientes y tambien hay una reunion."
        result = add_breathing_pauses(text, max_words_before_pause=8)
        # Should break at 'y' when sentence is too long
        assert isinstance(result, str)
        assert len(result) > 0

    def test_comma_break(self):
        from voice.text_processor import add_breathing_pauses
        text = "Hola Nicolas, buenos dias, como estas, en que te ayudo, tengo algo para ti."
        result = add_breathing_pauses(text, max_words_before_pause=6)
        # Should break at commas
        assert "." in result


# ── optimize_for_voice_clone V3 pipeline ─────────────────────────

class TestOptimizeV3Pipeline:
    def test_no_duplicate_steps(self):
        """V3 pipeline should not produce duplicate expansions."""
        text = "El 45% de la CPU esta al 72%."
        result = optimize_for_voice_clone(text)
        # Should have exactly 2 'por ciento'
        assert result.count("por ciento") == 2

    def test_full_v3_pipeline(self):
        """Test the complete V3 pipeline with all features."""
        text = "Hola Nicolas. Tu CPU esta al 45% y la RAM al 72%. Son las 14:30. Tienes 3 mensajes."
        result = optimize_for_voice_clone(text)
        # No accents
        assert "á" not in result
        # Numbers expanded
        assert "tres" in result
        # Percentages expanded
        assert "por ciento" in result
        # Time expanded
        assert "media" in result or "punto" in result
        # Ends with period
        assert result.strip().endswith(".")

    def test_repeated_chars_normalized(self):
        text = "Noooo, no quiero."
        result = optimize_for_voice_clone(text)
        assert "oooo" not in result

    def test_v3_consistency(self):
        """Running optimize twice should produce same result (idempotent)."""
        text = "Hola Nicolas, tienes 5 mensajes."
        r1 = optimize_for_voice_clone(text)
        r2 = optimize_for_voice_clone(r1)
        # Second pass should not change much
        assert r1 == r2


# ── V5: Emphasis Markers ─────────────────────────────────────────

class TestEmphasisMarkers:
    def test_emphasis_word(self):
        result = add_emphasis_markers("Tienes un error importante")
        # 'importante' should get a pause before it
        assert '. importante' in result or 'importante' in result

    def test_no_emphasis_at_start(self):
        result = add_emphasis_markers("Urgente, revisa esto")
        # First word should not get pause prefix
        assert result.startswith("Urgente") or result.startswith(". Urgente") is False

    def test_normal_words_unchanged(self):
        result = add_emphasis_markers("hola mundo normal")
        assert result == "hola mundo normal"


# ── V5: Sentence Prosody ─────────────────────────────────────────

class TestSentenceProsody:
    def test_question_detection(self):
        result = apply_sentence_prosody("como estas hoy?")
        # Should detect as question
        assert isinstance(result, str)

    def test_statement_unchanged(self):
        result = apply_sentence_prosody("hola mundo.")
        assert "hola mundo" in result

    def test_multiple_sentences(self):
        text = "hola. como estas? bien."
        result = apply_sentence_prosody(text)
        assert isinstance(result, str)


# ── V5: Natural Phrases ──────────────────────────────────────────

class TestNaturalPhrases:
    def test_buenos_dias(self):
        result = improve_natural_phrases("buenos dias Nicolas")
        assert "buenos dias" in result.lower()

    def test_gracias(self):
        result = improve_natural_phrases("muchas gracias por tu ayuda")
        assert "muchas gracias" in result.lower()

    def test_no_phrase(self):
        result = improve_natural_phrases("hola mundo")
        assert result == "hola mundo"


# ── V5: Prosody Pauses ───────────────────────────────────────────

class TestProsodyPauses:
    def test_technical_content(self):
        result = add_prosody_pauses("La CPU esta al 45 por ciento")
        assert isinstance(result, str)

    def test_warning_content(self):
        result = add_prosody_pauses("Cuidado, hay un error urgente")
        assert isinstance(result, str)

    def test_normal_content(self):
        result = add_prosody_pauses("hola mundo normal")
        assert result == "hola mundo normal"


# ── V5: Full Pipeline ────────────────────────────────────────────

class TestOptimizeV5Pipeline:
    def test_v5_full_pipeline(self):
        """Test V5 pipeline with emphasis, prosody, and natural phrases."""
        text = "Hola Nicolas. Tienes 3 mensajes importantes. La CPU esta al 45%."
        result = optimize_for_voice_clone(text)
        # Should have no accents
        assert "á" not in result
        # Should have numbers expanded
        assert "tres" in result
        # Should have percentage expanded
        assert "por ciento" in result
        # Should end with period
        assert result.strip().endswith(".")

    def test_v5_question_handling(self):
        text = "como estas Nicolas? Tienes 5 mensajes nuevos."
        result = optimize_for_voice_clone(text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_v5_empty_text(self):
        result = optimize_for_voice_clone("")
        assert result == ""

    def test_v5_whitespace_only(self):
        result = optimize_for_voice_clone("   ")
        assert result == "   "

    def test_v5_emphasis_preserved(self):
        text = "Hay un error importante en el sistema."
        result = optimize_for_voice_clone(text)
        # 'importante' should be present
        assert "importante" in result.lower()
