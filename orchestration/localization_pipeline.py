"""
ORCA - orchestration/localization_pipeline.py
Role 4 (Geospatial & Localization Engineer)

Provides SpeechToText, the class main.py's /voice-query endpoint depends on.

No translation step here: planner.py already detects language from the
transcribed text, and synthesizer.py already answers in that language via
Groq. This file's only job is speech -> text.

Install:
    pip install openai-whisper
"""

import whisper

WHISPER_MODEL_SIZE = "medium"  # use "small" for faster demo-day inference if CPU-only


class SpeechToText:
    def __init__(self, model_size: str = WHISPER_MODEL_SIZE):
        self.model = whisper.load_model(model_size)

    def transcribe(self, audio_path: str):
        """Returns (whisper_lang_code, transcribed_text). Language is auto-detected."""
        result = self.model.transcribe(audio_path, task="transcribe")
        return result["language"], result["text"].strip()
