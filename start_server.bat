@echo off
cd /d c:\Users\vedant.sharma\Documents\ai-youtube-generator\platform\backend
set SIMULATE_RENDER=1
set API_KEY_ADMIN=dev-admin-key
set API_KEY_CREATOR=dev-creator-key
uvicorn app.main:app --host 127.0.0.1 --port 8000
