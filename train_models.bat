@echo off
setlocal
title CryptoQuant - Model Trainer

echo.
echo  =========================================
echo    CRYPTOQUANT AI - LOCAL TRAINER
echo  =========================================
echo.

:: Ensure script is run from the project root
cd /d "%~dp0"

:: Check for virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment 'venv' not found.
    echo Please run these commands first:
    echo   python -m venv venv
    echo   venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/3] Activating virtual environment...
call venv\Scripts\activate.bat

echo [2/3] Setting PYTHONPATH to project root...
set PYTHONPATH=%CD%

echo [3/3] Starting training pipeline...
echo.
python local_train.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo [OK] Training complete. Models and predictions uploaded to cloud storage.
) else (
    echo [FAIL] Training failed with error code %ERRORLEVEL%. Check output above.
)
echo.
pause
endlocal
