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

import base64
import os
import tempfile
import asyncio
import traceback
import uuid
import json
from shapely.geometry import shape
from shapely.ops import unary_union

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestration.graph import run_query
from orchestration.localization_pipeline import SpeechToText, text_to_speech

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
    # Optional GPS coordinates sent from the frontend device.
    latitude: float | None = None
    longitude: float | None = None


class SafeRouteRequest(BaseModel):
    latitude: float
    longitude: float


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


# ---------------------------------------------------------------------------
# Boundary endpoint -- serves India's EEZ/IMBL boundary line for map rendering
# ---------------------------------------------------------------------------
BOUNDARY_GEOJSON_PATH = os.path.join(
    os.path.dirname(__file__), "orchestration", "data", "india_imbl_eez.geojson"
)

# Cached at process start -- the boundary file doesn't change at runtime.
_boundary_line_cache: list[list[list[float]]] | None = None


def _compute_boundary_line() -> list[list[list[float]]]:
    """
    Reads orchestration/data/india_imbl_eez.geojson, merges India's own EEZ
    features (excluding any stray neighboring-country features the file may
    contain), simplifies the outline for performant rendering, and returns
    the largest boundary segments as a list of [lat, lon] polylines --
    matching the shape react-leaflet's <Polyline positions={...}> expects
    for a multi-segment line (mainland coast + Andaman & Nicobar are
    disconnected pieces, so this can't be a single flat line).
    """
    with open(BOUNDARY_GEOJSON_PATH) as f:
        geojson = json.load(f)

    india_features = [
        f
        for f in geojson["features"]
        if f.get("properties", {}).get("SOVEREIGN1") == "India"
    ]
    if not india_features:
        raise ValueError("No India EEZ features found in boundary geojson")

    geometries = [shape(f["geometry"]) for f in india_features]
    boundary = unary_union(geometries)
    outline = boundary.boundary

    # 0.02 degrees (~2km) tolerance keeps the coastline shape recognizable
    # while cutting point count from ~10k down to a browser-friendly size.
    simplified = outline.simplify(0.02, preserve_topology=True)

    lines = (
        list(simplified.geoms)
        if simplified.geom_type == "MultiLineString"
        else [simplified]
    )

    # India's EEZ outline includes hundreds of small Andaman & Nicobar
    # islands as separate tiny rings -- keeping all of them makes the map
    # unusably slow. Keep only the largest 15 by geographic length: this
    # covers the mainland coastline, the main Andaman & Nicobar outline,
    # and the larger individual islands.
    lines_sorted = sorted(lines, key=lambda l: l.length, reverse=True)
    top_lines = lines_sorted[:15]

    segments = []
    for line in top_lines:
        coords = [[round(y, 4), round(x, 4)] for x, y in line.coords]
        segments.append(coords)

    return segments


@app.get("/boundary", summary="India's EEZ/IMBL boundary line for map rendering")
def get_boundary():
    """
    Returns India's EEZ boundary as a list of [lat, lon] polylines, for
    direct use as react-leaflet's <Polyline positions={...}> prop.

    Source: Marine Regions World EEZ v12, India-filtered.
    NOTE: approximate boundary, not for navigation.
    """
    global _boundary_line_cache
    try:
        if _boundary_line_cache is None:
            _boundary_line_cache = _compute_boundary_line()
        return {
            "boundary": _boundary_line_cache,
            "source": "MarineRegions-EEZv12-India",
            "disclaimer": "Approximate boundary, not for navigation.",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Could not load boundary data: {e}"
        )


from orchestration.agents.marine_data_agent import (
    _fetch_pfz_geojson,
    _transform_feature_to_zone,
    _build_mock_data,
)
from orchestration.agents.geospatial_agent import suggest_safe_route, _haversine_nm


@app.post("/safe-route", summary="Get safe route to nearest PFZ")
def safe_route(req: SafeRouteRequest):
    try:
        try:
            geojson = _fetch_pfz_geojson()
            features = geojson["features"]
            zones = [_transform_feature_to_zone(f, i) for i, f in enumerate(features)]
        except Exception as e:
            print(f"Failed to fetch real PFZ data, falling back to mock: {e}")
            zones = _build_mock_data()["pfz_zones"]

        if not zones:
            raise HTTPException(status_code=404, detail="No PFZ zones found")

        # Find nearest PFZ
        nearest_zone = None
        min_dist = float("inf")
        for z in zones:
            # Note: _transform_feature_to_zone returns "latitude" and "longitude"
            dist = _haversine_nm(
                req.latitude, req.longitude, z["latitude"], z["longitude"]
            )
            if dist < min_dist:
                min_dist = dist
                nearest_zone = z

        # Calculate safe route
        route = suggest_safe_route(
            req.latitude,
            req.longitude,
            nearest_zone["latitude"],
            nearest_zone["longitude"],
        )
        return {"route": route, "nearest_pfz": nearest_zone}
    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


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

    # Build user_location from GPS coordinates if both are provided.
    user_location: dict | None = None
    if request.latitude is not None and request.longitude is not None:
        user_location = {"lat": request.latitude, "lon": request.longitude}

    try:
        # Pass session_id and user_location — turn_id is auto-generated inside run_query.
        result = await asyncio.to_thread(
            run_query,
            raw_query=request.text,
            session_id=session_id,
            user_location=user_location,
        )
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
async def voice_query(
    audio: UploadFile = File(...),
    session_id: str | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
):
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
            whisper_lang, transcribed_text = _get_stt().transcribe(tmp_path)
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

        # Build user_location from GPS coordinates if both are provided.
        user_location: dict | None = None
        if latitude is not None and longitude is not None:
            user_location = {"lat": latitude, "lon": longitude}

        try:
            result = await asyncio.to_thread(
                run_query,
                raw_query=transcribed_text,
                session_id=session_id,
                user_location=user_location,
            )
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

        # Generate TTS audio for the final answer
        audio_b64 = None
        if result.final_answer:
            tts_lang = getattr(result, "language", None) or whisper_lang or "en"
            out_file = f"response_{uuid.uuid4().hex}.mp3"
            try:
                text_to_speech(result.final_answer, tts_lang, out_file)
                with open(out_file, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode("utf-8")
            except Exception as exc:
                print("Failed to generate TTS:", exc)
            finally:
                if os.path.exists(out_file):
                    os.unlink(out_file)

        return {
            **result_data,
            "transcribed_text": transcribed_text,
            "session_id": session_id,
            "audio_b64": audio_b64,
        }
    finally:
        os.unlink(tmp_path)
