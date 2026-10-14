@echo off
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
pause
