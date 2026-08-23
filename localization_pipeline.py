"""
ORCA - localization.py
Role 4 (Geospatial & Localization Engineer)

Regional Indian language voice in -> English text -> graph.run_query() ->
English answer -> regional language voice out.

This sits OUTSIDE the LangGraph pipeline (it is not one of the 5 specialist
agents in CONTRACTS.md) -- it wraps graph.run_query() at the entry/exit points,
converting voice to the English text the Planner/agents expect, and converting
the final English answer back to the fisherman's spoken language.

Install (see README section below for the full guide):
    pip install openai-whisper gTTS transformers sentencepiece torch torchaudio
"""

import whisper
from gtts import gTTS
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch

from orchestration.graph import run_query
from orchestration.state import TurnState

WHISPER_MODEL_SIZE = "medium"  # use "small" for faster demo-day inference if CPU-only

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


def run_localized_query(audio_path: str, user_location: dict | None = None, turn_id: str = "voice-turn") -> dict:
    """
    Full voice-in -> voice-out pipeline, wrapping the existing graph.run_query().

    Returns a dict with every intermediate step so it's easy to debug/demo
    which stage produced what -- useful for the live agent-trace panel too.
    """
    detected_lang, regional_text = speech_to_text(audio_path)
    english_query = indic_to_english(regional_text, detected_lang)

    state = TurnState(turn_id=turn_id, raw_query=english_query, user_location=user_location)
    result_state = run_query(english_query, turn_id=turn_id) if user_location is None else _run_with_location(state)

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


def _run_with_location(state: TurnState) -> TurnState:
    """graph.run_query() only takes raw_query today; this preserves user_location
    (needed by geospatial_agent) until Role 1 adds a location param upstream."""
    from orchestration.graph import app, _state_to_dict, _dict_to_state

    result = app.invoke(_state_to_dict(state))
    return _dict_to_state(result)


if __name__ == "__main__":
    # Quick manual test -- see README "How to test" section for how to get a sample audio file
    output = run_localized_query("sample_query.wav", user_location={"lat": 15.5, "lon": 73.8})
    print(output)
