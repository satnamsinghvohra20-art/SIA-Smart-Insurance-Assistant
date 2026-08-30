@echo off
echo Starting S.I.A. (Smart Insurance Assistant) Multi-Agent Kernel backend...
start cmd /k "python -m uvicorn backend.main:app --port 8000"
echo Opening S.I.A. Dashboard in default browser...
start "" "frontend\index.html"
echo S.I.A. (Smart Insurance Assistant) is now running. Close the backend command window to stop the server.
pause
