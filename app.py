import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from faster_whisper import WhisperModel
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

APP_API_KEY = os.getenv("AUDIO_API_KEY", "").strip()
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base").strip() or "base"
DEVICE = os.getenv("WHISPER_DEVICE", "cpu").strip() or "cpu"
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8").strip() or "int8"
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "100"))
SUPPORTED_EXTENSIONS = {
    ".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus",
    ".webm", ".mp4", ".mpeg", ".mpga", ".wma"
}

app = FastAPI(
    title="Local Speech-to-Text API",
    description="Transcribe audio locally using faster-whisper. No Groq/API provider key required.",
    version="1.0.0",
)

_model: Optional[WhisperModel] = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        # The selected Whisper model is downloaded automatically on first use.
        _model = WhisperModel(
            MODEL_SIZE,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
        )
    return _model


def check_api_key(provided: Optional[str]) -> None:
    # Authentication is optional for local development. Set AUDIO_API_KEY in .env to enable it.
    if APP_API_KEY and provided != APP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html><head><title>Local Speech-to-Text</title></head>
    <body style="font-family:Arial;max-width:720px;margin:40px auto;line-height:1.5">
    <h1>Local Speech-to-Text API</h1>
    <p>Transcription runs locally using faster-whisper. No Groq key is needed.</p>
    <p>Open <a href="/docs">/docs</a> to upload an audio file.</p>
    <p>Supported extensions include WAV, MP3, M4A, AAC, FLAC, OGG, OPUS, WebM and MP4,
    subject to the installed audio decoder and file validity.</p>
    </body></html>
    """


@app.get("/health")
def health():
    return {
        "status": "ok",
        "provider": "local faster-whisper",
        "model": MODEL_SIZE,
        "device": DEVICE,
        "authentication_enabled": bool(APP_API_KEY),
    }


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    check_api_key(x_api_key)

    filename = file.filename or "audio"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{suffix or '(none)'}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_FILE_MB} MB limit.")

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(content)
            temp_path = temp.name

        model = get_model()
        segments_iter, info = model.transcribe(
            temp_path,
            beam_size=5,
            vad_filter=True,
            word_timestamps=False,
        )

        segments = []
        full_text_parts = []
        for index, segment in enumerate(segments_iter):
            text = segment.text.strip()
            segments.append({
                "segment_id": index,
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "text": text,
            })
            if text:
                full_text_parts.append(text)

        return {
            "filename": filename,
            "detected_format_by_extension": suffix.lstrip("."),
            "language": info.language,
            "language_probability": round(float(info.language_probability), 4),
            "duration_seconds": round(float(info.duration), 3),
            "full_text": " ".join(full_text_parts),
            "segments": segments,
            "segment_count": len(segments),
            "transcription_engine": "faster-whisper (local)",
            "model": MODEL_SIZE,
        }

    except HTTPException:
        raise
    except Exception as exc:
        # Useful details are printed to the terminal; the client gets a readable message.
        print(f"Transcription error: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {type(exc).__name__}: {exc}. Check the terminal for details.",
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        await file.close()
