\# How to Run BhaktiGen Locally (Current Layout)



Repo layout (relevant parts):



\- `backend/` – FastAPI + orchestrator (this folder)

\- `backend/frontend/` – React + Vite frontend

\- `backend/dev-start.ps1` – helper script for local dev \& tests



---



\## 1. Backend: Python API



\### Prereqs



\- Python 3.10+

\- FFmpeg installed and on PATH



\### Setup



```powershell

cd C:\\Users\\vedant.sharma\\Documents\\ai-youtube-generator\\backend



python -m venv .venv

.\\.venv\\Scripts\\activate



pip install -r requirements.txt



