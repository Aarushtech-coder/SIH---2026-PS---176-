"""
ORCA - localization.py
Role 4 (Geospatial & Localization Engineer)

Regional Indian language voice in -> ORCA pipeline -> regional language voice out.

IMPORTANT: planner.py already detects state.language from the transcribed text
(Unicode script or Groq), and synthesizer.py already asks Groq to write
final_answer directly in that language. So this module does NOT do its own
text translation -- that would duplicate/conflict with what the pipeline
already does. This module's job is only:
    1. speech -> text (Whisper), any supported Indian language
    2. hand the transcribed text to the existing graph.run_query() unchanged
    3. take the already-correct-language final_answer and speak it (gTTS)

Known gap (raise with Role 1): graph.run_query(raw_query, session_id, turn_id)
has no user_location parameter -- location is only inherited from a previous
turn via planner.resolve_context(). There is currently no way to set location
on a fresh/first turn. geospatial_agent falls back to MOCK data until this is
added upstream.

Install:
    pip install openai-whisper gTTS
"""

import whisper
from gtts import gTTS

from orchestration.graph import run_query

WHISPER_MODEL_SIZE = "medium"  # use "small" for faster demo-day inference if CPU-only

_whisper_model = None


class SpeechToText:
    """Thin class wrapper around the module-level speech_to_text() function.

    Instantiated lazily in main.py so the Whisper model is only loaded on the
    first /voice-query request, not at startup.
    """

    def transcribe(self, audio_path: str):
        """Returns (whisper_lang_code, transcribed_text)."""
        return speech_to_text(audio_path)


def _load_whisper():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
    return _whisper_model


def speech_to_text(audio_path: str):
    """Returns (whisper_lang_code, transcribed_text). Language is auto-detected."""
    model = _load_whisper()
    result = model.transcribe(audio_path, task="transcribe")
    return result["language"], result["text"].strip()


def text_to_speech(text: str, lang_code: str, output_path: str = "response.mp3") -> str:
    """gTTS uses simple ISO codes ('hi', 'ta', etc.) -- same codes Whisper returns."""
    tts = gTTS(text=text, lang=lang_code)
    tts.save(output_path)
    return output_path


def run_localized_query(audio_path: str, session_id: str = "default", turn_id: str | None = None) -> dict:
    """
    Full voice-in -> voice-out pipeline, wrapping the real graph.run_query()
    unchanged. Returns every intermediate step for easy debugging/demo.
    """
    detected_lang, transcribed_text = speech_to_text(audio_path)

    # Hand the raw transcribed text straight to the real pipeline -- planner.py
    # detects state.language from this same text, and synthesizer.py answers
    # in that language automatically. No manual translation step needed here.
    result_state = run_query(transcribed_text, session_id=session_id, turn_id=turn_id)

    final_answer = result_state.final_answer or ""

    # Use the pipeline's own detected language (state.language) for TTS if it
    # differs from Whisper's guess -- state.language is what the answer was
    # actually written in.
    tts_lang = result_state.language or detected_lang
    audio_out_path = text_to_speech(final_answer, tts_lang)

    return {
        "whisper_detected_language": detected_lang,
        "pipeline_detected_language": result_state.language,
        "transcribed_text": transcribed_text,
        "final_answer": final_answer,
        "audio_output_path": audio_out_path,
        "intent": result_state.intent,
        "trace": result_state.trace,
    }


if __name__ == "__main__":
    # Quick manual test -- record a short clip of yourself speaking a query,
    # save as sample_query.wav in the repo root, then run this file directly.
    output = run_localized_query("sample_query.wav")
    print(output)
