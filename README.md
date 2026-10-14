# Local Speech-to-Text API (No Groq)

This project uses **faster-whisper** to transcribe audio locally. It does not call Groq or require a Groq API key. FFmpeg is not a separate requirement for the standard `faster-whisper` install because audio decoding is handled through PyAV; if a particular media file cannot be decoded, install FFmpeg and convert it to WAV/MP3.

## Features
- FastAPI endpoint: `POST /transcribe`
- Segment-level timestamps: `start`, `end`, `text`
- Detected language and language confidence
- Local transcription; no per-minute cloud transcription API charge
- Common formats: WAV, MP3, M4A, AAC, FLAC, OGG, OPUS, WebM, MP4 (actual decoding depends on file/container/codec support)
- Optional app-level `X-API-Key` protection
- Swagger UI at `/docs`

## Windows setup
1. Extract this ZIP and open the extracted folder in VS Code.
2. Open a terminal in this folder.
3. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

   If PowerShell blocks activation, you can skip activation and use `.venv\Scripts\python.exe -m pip install -r requirements.txt`, then run with `.venv\Scripts\python.exe -m uvicorn app:app --reload`.

4. Copy `.env.example` to `.env`. For local testing, `AUDIO_API_KEY=` can remain blank. If you want endpoint authentication, generate a key:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Put it after `AUDIO_API_KEY=` in `.env`, without surrounding quotes or spaces, then restart the app.
5. Start the server:

   ```powershell
   python -m uvicorn app:app --reload
   ```
6. Open http://127.0.0.1:8000/docs
7. Select `POST /transcribe`, click **Try it out**, upload an audio file, then click **Execute**.
8. If `AUDIO_API_KEY` is set, provide that exact value in the `X-API-Key` field. If it is blank, leave the header empty.

## First run note
The first transcription downloads the Whisper model specified by `WHISPER_MODEL` (default `base`). This needs an internet connection and can take a few minutes. After download, inference runs locally. A larger model may be more accurate but uses more memory and is slower. `tiny` is faster but generally less accurate.

## Example response
```json
{
  "filename": "test_audio.wav",
  "detected_format_by_extension": "wav",
  "language": "en",
  "language_probability": 0.9876,
  "duration_seconds": 5.2,
  "full_text": "Hello, this is a test.",
  "segments": [
    {
      "segment_id": 0,
      "start": 0.0,
      "end": 2.4,
      "text": "Hello, this is a test."
    }
  ],
  "segment_count": 1,
  "transcription_engine": "faster-whisper (local)",
  "model": "base"
}
```

The sample response above is illustrative; actual segment boundaries and detected language depend on the uploaded audio.

## Troubleshooting
- **First request takes a long time:** model download or first-time model initialization.
- **Memory/CPU is too high:** set `WHISPER_MODEL=tiny` in `.env` and restart.
- **Model download fails:** check internet access, then retry.
- **Unsupported/corrupt audio:** convert the file to WAV or MP3 with FFmpeg, then upload again.
- **401 Invalid or missing X-API-Key:** either provide the exact `AUDIO_API_KEY` or leave it blank in `.env` for local testing.
- **Port already in use:** run `python -m uvicorn app:app --reload --port 8001`.

## Privacy
Audio is processed by the local machine running this API. The Whisper model is downloaded from the model hosting infrastructure on first use. Do not expose this local development server publicly without authentication and deployment hardening.
