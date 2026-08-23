"""
ORCA - Role 4 Localization Pipeline
Regional Indian language voice input -> English reasoning -> Regional language voice output

Pipeline: Whisper (STT) -> IndicTrans2 (translation) -> gTTS (TTS)

SETUP (run once):
    pip install openai-whisper gTTS torch torchaudio
    pip install git+https://github.com/AI4Bharat/IndicTrans2.git
    # or use the simpler HF pipeline route shown below (recommended for hackathon speed)
    pip install transformers sentencepiece

NOTE: First run will download model weights (Whisper ~1.5GB for 'medium',
IndicTrans2 ~1-2GB). Do this once, well before your demo, on your dev machine's
own internet connection -- do not rely on venue wifi to download models live.
"""

import whisper
from gtts import gTTS
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import os

# ---------------------------------------------------------------------------
# 1. CONFIG - adjust target language here
# ---------------------------------------------------------------------------
# Whisper language codes for Indian languages (use ISO 639-1)
SUPPORTED_LANGUAGES = {
    "hindi": "hi",
    "tamil": "ta",
    "telugu": "te",
    "marathi": "mr",
    "bengali": "bn",
    "gujarati": "gu",
    "malayalam": "ml",
    "kannada": "kn",
    "urdu": "ur",
    "odia": "or",
    "punjabi": "pa",
}

WHISPER_MODEL_SIZE = "medium"  # use "large-v3" for best Indian-language accuracy if you have GPU

# IndicTrans2 model names (HuggingFace)
INDIC_TO_EN_MODEL = "ai4bharat/indictrans2-indic-en-1B"
EN_TO_INDIC_MODEL = "ai4bharat/indictrans2-en-indic-1B"


# ---------------------------------------------------------------------------
# 2. SPEECH TO TEXT (Whisper)
# ---------------------------------------------------------------------------
class SpeechToText:
    def __init__(self, model_size=WHISPER_MODEL_SIZE):
        print(f"Loading Whisper model ({model_size})...")
        self.model = whisper.load_model(model_size)

    def transcribe(self, audio_path: str, language: str = None):
        """
        audio_path: path to .mp3/.wav/.m4a file
        language: optional ISO code (e.g. 'hi') to force language; omit for auto-detect
        Returns: (detected_language_code, transcribed_text)
        """
        result = self.model.transcribe(audio_path, language=language, task="transcribe")
        return result["language"], result["text"].strip()


# ---------------------------------------------------------------------------
# 3. TRANSLATION (IndicTrans2)
# ---------------------------------------------------------------------------
class Translator:
    def __init__(self):
        print("Loading IndicTrans2 models (this can take a minute on first run)...")
        self.indic_en_tok = AutoTokenizer.from_pretrained(INDIC_TO_EN_MODEL, trust_remote_code=True)
        self.indic_en_model = AutoModelForSeq2SeqLM.from_pretrained(INDIC_TO_EN_MODEL, trust_remote_code=True)

        self.en_indic_tok = AutoTokenizer.from_pretrained(EN_TO_INDIC_MODEL, trust_remote_code=True)
        self.en_indic_model = AutoModelForSeq2SeqLM.from_pretrained(EN_TO_INDIC_MODEL, trust_remote_code=True)

    def indic_to_english(self, text: str, src_lang_tag: str):
        """src_lang_tag example: 'hin_Deva', 'tam_Taml' -- IndicTrans2 uses FLORES-200 tags"""
        inputs = self.indic_en_tok(text, return_tensors="pt", padding=True)
        with torch.no_grad():
            output = self.indic_en_model.generate(**inputs, max_length=256, num_beams=5)
        return self.indic_en_tok.decode(output[0], skip_special_tokens=True)

    def english_to_indic(self, text: str, tgt_lang_tag: str):
        """tgt_lang_tag example: 'hin_Deva', 'tam_Taml'"""
        inputs = self.en_indic_tok(text, return_tensors="pt", padding=True)
        with torch.no_grad():
            output = self.en_indic_model.generate(**inputs, max_length=256, num_beams=5)
        return self.en_indic_tok.decode(output[0], skip_special_tokens=True)


# FLORES-200 language tags needed by IndicTrans2 (map from Whisper's simple codes)
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


# ---------------------------------------------------------------------------
# 4. TEXT TO SPEECH (gTTS)
# ---------------------------------------------------------------------------
class TextToSpeech:
    def synthesize(self, text: str, lang_code: str, output_path: str = "response.mp3"):
        """lang_code: gTTS uses simple codes like 'hi', 'ta', 'te' etc."""
        tts = gTTS(text=text, lang=lang_code)
        tts.save(output_path)
        return output_path


# ---------------------------------------------------------------------------
# 5. FULL PIPELINE
# ---------------------------------------------------------------------------
class LocalizationPipeline:
    def __init__(self):
        self.stt = SpeechToText()
        self.translator = Translator()
        self.tts = TextToSpeech()

    def process_query(self, audio_path: str, answer_fn):
        """
        audio_path: incoming fisherman voice query (any supported Indian language)
        answer_fn: your reasoning pipeline function, takes English text -> returns English answer
                   (this is where you'd call your Planner Agent / geofencing logic)
        Returns: dict with all intermediate + final outputs
        """
        # Step 1: Regional speech -> regional text (auto-detect language)
        detected_lang, regional_text = self.stt.transcribe(audio_path)
        print(f"Detected language: {detected_lang}")
        print(f"Transcribed: {regional_text}")

        flores_tag = FLORES_TAGS.get(detected_lang)
        if not flores_tag:
            raise ValueError(f"Language '{detected_lang}' not in supported FLORES tag map")

        # Step 2: Regional text -> English
        english_query = self.translator.indic_to_english(regional_text, flores_tag)
        print(f"English query: {english_query}")

        # Step 3: Your reasoning/agent pipeline runs here
        english_answer = answer_fn(english_query)
        print(f"English answer: {english_answer}")

        # Step 4: English -> regional text
        regional_answer = self.translator.english_to_indic(english_answer, flores_tag)
        print(f"Regional answer: {regional_answer}")

        # Step 5: Regional text -> speech
        audio_out = self.tts.synthesize(regional_answer, detected_lang, "response.mp3")
        print(f"Audio response saved to: {audio_out}")

        return {
            "detected_language": detected_lang,
            "transcribed_text": regional_text,
            "english_query": english_query,
            "english_answer": english_answer,
            "regional_answer": regional_answer,
            "audio_output_path": audio_out,
        }


# ---------------------------------------------------------------------------
# 6. EXAMPLE USAGE
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    def dummy_reasoning(english_query: str) -> str:
        """Placeholder for your Planner Agent / geofencing logic."""
        return "Yes, it is safe to sail tomorrow. The nearest fishing zone is 12 kilometers away."

    pipeline = LocalizationPipeline()
    result = pipeline.process_query("sample_query.wav", dummy_reasoning)
    print("\n--- Final Result ---")
    print(result)
