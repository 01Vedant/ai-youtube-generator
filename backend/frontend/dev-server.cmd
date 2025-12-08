@echo off
REM Frontend development server startup script
REM Uses portable Node.js installation

SET NODE_PATH=C:\Users\vedant.sharma\Documents\node-portable\node-v24.11.1-win-x64
SET PATH=%NODE_PATH%;%PATH%

cd /d %~dp0
echo Starting Vite development server...
call "%NODE_PATH%\npm.cmd" run dev
