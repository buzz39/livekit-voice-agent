"""Tests for Sarvam TTS integration (official plugin + language normalization)."""

import pytest

from outbound.sarvam_tts import (
    SARVAM_DEFAULT_LANGUAGE,
    SARVAM_DEFAULT_MODEL,
    SARVAM_DEFAULT_VOICE,
    SARVAM_SAMPLE_RATE,
    normalize_sarvam_language,
    normalize_sarvam_model,
    normalize_sarvam_speaker,
)


# --- Language normalization ---

def test_normalize_sarvam_language_passes_valid_bcp47():
    assert normalize_sarvam_language("hi-IN") == "hi-IN"
    assert normalize_sarvam_language("en-IN") == "en-IN"
    assert normalize_sarvam_language("ta-IN") == "ta-IN"


def test_normalize_sarvam_language_resolves_aliases():
    assert normalize_sarvam_language("english") == "en-IN"
    assert normalize_sarvam_language("hindi") == "hi-IN"
    assert normalize_sarvam_language("hinglish") == "en-IN"
    assert normalize_sarvam_language("en") == "en-IN"
    assert normalize_sarvam_language("en-US") == "en-IN"
    assert normalize_sarvam_language("hi") == "hi-IN"
    assert normalize_sarvam_language("tamil") == "ta-IN"
    assert normalize_sarvam_language("bengali") == "bn-IN"
    assert normalize_sarvam_language("telugu") == "te-IN"


def test_normalize_sarvam_language_returns_default_for_none():
    assert normalize_sarvam_language(None) == SARVAM_DEFAULT_LANGUAGE
    assert normalize_sarvam_language("") == SARVAM_DEFAULT_LANGUAGE


def test_normalize_sarvam_language_returns_default_for_unknown():
    assert normalize_sarvam_language("klingon") == SARVAM_DEFAULT_LANGUAGE


# --- Speaker normalization ---

def test_normalize_sarvam_speaker_passes_valid():
    assert normalize_sarvam_speaker("simran") == "simran"
    assert normalize_sarvam_speaker("rahul") == "rahul"


def test_normalize_sarvam_speaker_normalizes_case():
    assert normalize_sarvam_speaker("Simran") == "simran"
    assert normalize_sarvam_speaker("RAHUL") == "rahul"


def test_normalize_sarvam_speaker_returns_default_for_invalid():
    assert normalize_sarvam_speaker(None) == SARVAM_DEFAULT_VOICE
    assert normalize_sarvam_speaker("nonexistent") == SARVAM_DEFAULT_VOICE


# --- Model normalization ---

def test_normalize_sarvam_model_passes_valid():
    assert normalize_sarvam_model("bulbul:v2") == "bulbul:v2"
    assert normalize_sarvam_model("bulbul:v3") == "bulbul:v3"
    assert normalize_sarvam_model("bulbul:v3-beta") == "bulbul:v3-beta"


def test_normalize_sarvam_model_returns_default_for_invalid():
    assert normalize_sarvam_model(None) == SARVAM_DEFAULT_MODEL
    assert normalize_sarvam_model("tts-1") == SARVAM_DEFAULT_MODEL
    assert normalize_sarvam_model("sarvam") == SARVAM_DEFAULT_MODEL


# --- Official plugin instantiation ---

def test_official_sarvam_tts_instantiates_with_correct_params():
    from livekit.plugins.sarvam import TTS
    tts = TTS(
        target_language_code="en-IN",
        model="bulbul:v3",
        speaker="simran",
        speech_sample_rate=8000,
        api_key="test-key",
    )
    assert tts._opts.speaker == "simran"
    assert tts._opts.model == "bulbul:v3"
    assert str(tts._opts.target_language_code) == "en-IN"
    assert tts.sample_rate == 8000


def test_official_sarvam_tts_default_sample_rate_is_22050():
    from livekit.plugins.sarvam import TTS
    tts = TTS(
        target_language_code="hi-IN",
        api_key="test-key",
    )
    assert tts.sample_rate == 22050


def test_sarvam_sample_rate_constant_is_8000():
    """PSTN requires 8kHz - our constant must match."""
    assert SARVAM_SAMPLE_RATE == 8000


def test_normalize_sarvam_language_maps_aliases_to_supported_codes():
    assert normalize_sarvam_language("english") == "en-IN"
    assert normalize_sarvam_language("hinglish") == "en-IN"
    assert normalize_sarvam_language("hi") == "hi-IN"
    assert normalize_sarvam_language("en-US") == "en-IN"
    assert normalize_sarvam_language("invalid-language") == "en-IN"