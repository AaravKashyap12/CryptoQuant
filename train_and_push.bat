@echo off
setlocal

cd /d "%~dp0"

echo.
echo =========================================
echo   CRYPTOQUANT - TRAIN, COMMIT, PUSH
echo =========================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Run these first:
    echo   python -m venv venv
    echo   venv\Scripts\pip install -r requirements.local.txt
    exit /b 1
)

echo [1/5] Training frontend TF.js models...
"%CD%\venv\Scripts\python.exe" local_train.py
if errorlevel 1 (
    echo [FAIL] Training failed. Not committing or pushing.
    exit /b 1
)

echo.
echo [2/5] Staging generated model files...
git add frontend/public/models
if errorlevel 1 (
    echo [FAIL] Could not stage model files.
    exit /b 1
)

echo.
echo [3/5] Checking whether model files changed...
git diff --cached --quiet
if %ERRORLEVEL% EQU 0 (
    echo [OK] No model changes to commit.
    exit /b 0
)

echo.
echo [4/5] Committing model updates...
git commit -m "Update trained frontend models"
if errorlevel 1 (
    echo [FAIL] Commit failed. Not pushing.
    exit /b 1
)

echo.
echo [5/5] Pushing to GitHub...
git push
if errorlevel 1 (
    echo [FAIL] Push failed. Commit was created locally.
    exit /b 1
)

echo.
echo [OK] Models pushed. Vercel should redeploy automatically.
endlocal
