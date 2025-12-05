@echo off
REM Start the LiveKit telephony agent (Windows)

echo Starting LiveKit AI Telephony Agent...
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo Error: .env file not found!
    echo Please copy .env.example to .env and configure your credentials.
    exit /b 1
)

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Run the agent
python telephony_agent.py
