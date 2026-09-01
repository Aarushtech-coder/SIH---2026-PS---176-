"""
ORCA - orchestration/voice_pipeline_full.py
Role 4 (Geospatial & Localization Engineer)

OPTIONAL, ADDITIVE full voice pipeline with an explicit, inspectable
translation step (IndicTrans2), separate from main.py's existing
/voice-query endpoint. Does not modify or replace any teammate's code.

Full chain: Whisper (STT) -> IndicTrans2 (regional -> English)
            -> orchestration.graph.run_query() (unchanged)
            -> IndicTrans2 (English -> regional) -> gTTS (TTS)

When you'd want this over main.py's /voice-query:
    - You want a visible, named "translation model" step for your
      architecture diagram / judge Q&A, not an implicit LLM behavior
    - You want deterministic translation output you can inspect/debug
    - You want a fallback path if Groq's answer quality in a given
      language is weaker than a dedicated translation model

Trade-off to be upfront about: this DOUBLES the localization work,
since synthesizer.py already answers directly in the detected language
via Groq. Using both together on the same request would translate
twice. Pick one path per request, not both.

Install:
    pip install openai-whisper gTTS transformers sentencepiece torch torchaudio
"""

import torch
import whisper
from gtts import gTTS
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from orchestration.graph import run_query

WHISPER_MODEL_SIZE = "medium"

INDIC_TO_EN_MODEL = "ai4bharat/indictrans2-indic-en-1B"
EN_TO_INDIC_MODEL = "ai4bharat/indictrans2-en-indic-1B"

# Whisper language code -> FLORES-200 tag (required by IndicTrans2)
FLORES_TAGS = {
    "hi": "hin_Deva",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "mr": "mar_Deva",
    "bn": "ben_Beng",
    "gu": "guj_Gujr",
    "ml": "mal_Mlym",
    "kn": "kan_Knda",
    "ur": "urd_Arab",
    "or": "ory_Orya",
    "pa": "pan_Guru",
}

_whisper_model = None
_indic_en_tok = _indic_en_model = None
_en_indic_tok = _en_indic_model = None


def _load_models():
    """Lazy-load so importing this module doesn't force a multi-GB download."""
    global _whisper_model, _indic_en_tok, _indic_en_model, _en_indic_tok, _en_indic_model

    if _whisper_model is None:
        _whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)

    if _indic_en_model is None:
        _indic_en_tok = AutoTokenizer.from_pretrained(INDIC_TO_EN_MODEL, trust_remote_code=True)
        _indic_en_model = AutoModelForSeq2SeqLM.from_pretrained(INDIC_TO_EN_MODEL, trust_remote_code=True)

    if _en_indic_model is None:
        _en_indic_tok = AutoTokenizer.from_pretrained(EN_TO_INDIC_MODEL, trust_remote_code=True)
        _en_indic_model = AutoModelForSeq2SeqLM.from_pretrained(EN_TO_INDIC_MODEL, trust_remote_code=True)


def speech_to_text(audio_path: str):
    """Returns (whisper_lang_code, transcribed_text)."""
    _load_models()
    result = _whisper_model.transcribe(audio_path, task="transcribe")
    return result["language"], result["text"].strip()


def indic_to_english(text: str, whisper_lang_code: str) -> str:
    _load_models()
    flores_tag = FLORES_TAGS.get(whisper_lang_code)
    if not flores_tag:
        raise ValueError(f"Unsupported language for translation: {whisper_lang_code}")
    inputs = _indic_en_tok(text, return_tensors="pt", padding=True)
    with torch.no_grad():
        output = _indic_en_model.generate(**inputs, max_length=256, num_beams=5)
    return _indic_en_tok.decode(output[0], skip_special_tokens=True)


def english_to_indic(text: str, whisper_lang_code: str) -> str:
    _load_models()
    flores_tag = FLORES_TAGS.get(whisper_lang_code)
    if not flores_tag:
        raise ValueError(f"Unsupported language for translation: {whisper_lang_code}")
    inputs = _en_indic_tok(text, return_tensors="pt", padding=True)
    with torch.no_grad():
        output = _en_indic_model.generate(**inputs, max_length=256, num_beams=5)
    return _en_indic_tok.decode(output[0], skip_special_tokens=True)


def text_to_speech(text: str, whisper_lang_code: str, output_path: str = "response.mp3") -> str:
    tts = gTTS(text=text, lang=whisper_lang_code)
    tts.save(output_path)
    return output_path


def run_full_voice_pipeline(audio_path: str, session_id: str = "default", turn_id: str | None = None) -> dict:
    """
    Full explicit pipeline: STT -> translate-to-English -> run_query()
    -> translate-to-regional -> TTS. Every intermediate step is returned
    for a visible trace/demo panel.

    NOTE: this calls run_query() with the ENGLISH translation, not the
    original regional text -- unlike main.py's /voice-query, which passes
    the regional text straight through and lets synthesizer.py answer in
    that language directly. Don't call both paths for the same request.
    """
    detected_lang, regional_text = speech_to_text(audio_path)
    english_query = indic_to_english(regional_text, detected_lang)

    result_state = run_query(english_query, session_id=session_id, turn_id=turn_id)
    english_answer = result_state.final_answer or ""

    regional_answer = english_to_indic(english_answer, detected_lang)
    audio_out_path = text_to_speech(regional_answer, detected_lang)

    return {
        "detected_language": detected_lang,
        "transcribed_text": regional_text,
        "english_query": english_query,
        "english_answer": english_answer,
        "regional_answer": regional_answer,
        "audio_output_path": audio_out_path,
        "trace": result_state.trace,
    }


if __name__ == "__main__":
    # Quick manual test -- record a short clip of yourself speaking a query,
    # save as sample_query.wav in the repo root, then run this file directly.
    output = run_full_voice_pipeline("sample_query.wav")
    print(output)
