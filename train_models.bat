@if "%~1"=="RELAUNCHED" goto :main
@cmd /k "%~f0" RELAUNCHED
@exit

:main
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
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo [1/3] Activating virtual environment...
call venv\Scripts\activate.bat || (
    echo [ERROR] Failed to activate virtual environment.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

:: Bypass pyenv by calling venv Python directly
set PYTHON_EXE=%CD%\venv\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Cannot find venv Python at: %PYTHON_EXE%
    echo Rebuild the venv with: python -m venv venv
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo [2/3] Setting PYTHONPATH to project root...
set PYTHONPATH=%CD%

echo [3/3] Starting training pipeline...
echo.

"%PYTHON_EXE%" local_train.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo [OK] Training complete. Models and predictions uploaded to cloud storage.
) else (
    echo [FAIL] Training failed with error code %ERRORLEVEL%. Check output above.
)

echo.
echo Press any key to exit...
pause >nul
endlocal