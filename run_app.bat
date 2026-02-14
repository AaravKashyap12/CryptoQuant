@echo off
echo Starting Crypto Price Predictor V2 (React + FastAPI)...

start "Backend API" cmd /k "cd backend && ..\.venv\Scripts\python -m uvicorn main:app --reload --port 8001"
start "Frontend UI" cmd /k "cd frontend && npm.cmd run dev"

echo Services started!
echo Backend: http://localhost:8000/docs
echo Frontend: http://localhost:5173
pause
