# =============================================================================
# ORCA Orchestration API — HTTP wrapper around orchestration/graph.py
# =============================================================================
# How to run:
#   uvicorn main:app --reload --port 8000
#
# Note: The frontend should point to http://localhost:8000/query
# =============================================================================

# Load environment variables FIRST — before any other imports that may need them.
from dotenv import load_dotenv

load_dotenv()

import os
import tempfile
import traceback
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestration.graph import run_query
from orchestration.localization_pipeline import SpeechToText

# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ORCA Orchestration API",
    description="HTTP interface for the ORCA Planner → Agents → Synthesizer pipeline.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS middleware
# NOTE: allow_origins=["*"] is intentionally permissive because this API is
# for local judge demos only, running on localhost — NOT for production use.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    text: str
    # session_id links this call to a prior conversation turn for multi-turn
    # context resolution. The frontend should persist it from the response and
    # send it back on subsequent calls within the same session.
    session_id: str | None = None


# ---------------------------------------------------------------------------
# Whisper model — loaded lazily on first voice request, then cached, so
# `uvicorn --reload` startup and text-only requests aren't slowed down by a
# ~1.5GB model load nobody asked for yet.
# ---------------------------------------------------------------------------
_stt: SpeechToText | None = None


def _get_stt() -> SpeechToText:
    global _stt
    if _stt is None:
        _stt = SpeechToText()
    return _stt


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", summary="Root — API info")
async def root():
    """Short landing page so hitting the base URL isn't a confusing 404."""
    return {
        "message": "Welcome to the ORCA Orchestration API.",
        "endpoints": {
            "health": "GET /health",
            "query": "POST /query",
            "voice_query": "POST /voice-query",
        },
    }


@app.get("/health", summary="Health check")
async def health():
    """Simple liveness probe."""
    return {"status": "ok", "message": "ORCA orchestration API is running"}


@app.post("/query", summary="Run the ORCA pipeline")
async def query(request: QueryRequest):
    """
    Accepts a natural-language query, runs the full
    Planner → Agents → Synthesizer pipeline, and returns a TurnState.
    Pass the returned session_id back in subsequent requests to enable
    multi-turn context resolution.
    """
    # Validate that text is not empty / whitespace-only.
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Bad Request",
                "message": "'text' must be a non-empty, non-whitespace string.",
            },
        )

    # Use the provided session_id or generate a fresh one for a new session.
    session_id = request.session_id or str(uuid.uuid4())

    try:
        # Pass session_id correctly — turn_id is auto-generated inside run_query.
        result = run_query(raw_query=request.text, session_id=session_id)
    except Exception as exc:
        # Print the full traceback to the server console for hackathon debugging.
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal Server Error",
                "message": f"Pipeline raised an unexpected exception: {exc}",
            },
        )

    # Support both Pydantic v1 (.dict()) and v2 (.model_dump()).
    result_data = (
        result.model_dump() if hasattr(result, "model_dump") else result.dict()
    )

    # Include session_id in the response so the frontend can persist and reuse it.
    return {**result_data, "session_id": session_id}


@app.post("/voice-query", summary="Run the ORCA pipeline from a voice recording")
async def voice_query(audio: UploadFile = File(...), session_id: str | None = Form(None)):
    """
    Accepts a recorded audio clip in any language Whisper supports, transcribes
    it, then runs the same Planner -> Agents -> Synthesizer pipeline as
    POST /query. No separate translation step is needed here: planner.py
    already detects the transcribed text's language and synthesizer.py
    already replies in it.
    """
    suffix = os.path.splitext(audio.filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        try:
            _, transcribed_text = _get_stt().transcribe(tmp_path)
        except Exception as exc:
            traceback.print_exc()
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "Transcription Failed",
                    "message": f"Could not transcribe audio: {exc}",
                },
            )

        if not transcribed_text or not transcribed_text.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Bad Request",
                    "message": "No speech detected in the recording.",
                },
            )

        session_id = session_id or str(uuid.uuid4())

        try:
            result = run_query(raw_query=transcribed_text, session_id=session_id)
        except Exception as exc:
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal Server Error",
                    "message": f"Pipeline raised an unexpected exception: {exc}",
                },
            )

        result_data = (
            result.model_dump() if hasattr(result, "model_dump") else result.dict()
        )
        return {**result_data, "transcribed_text": transcribed_text, "session_id": session_id}
    finally:
        os.unlink(tmp_path)
