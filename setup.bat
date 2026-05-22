@echo off
echo ============================================
echo  PinAffiliateBot — Windows Setup
echo ============================================
echo.

echo [1/4] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Install from python.org
    pause
    exit /b 1
)

echo [2/4] Installing dependencies...
pip install -r requirements.txt

echo [3/4] Creating folders...
mkdir output\images 2>nul
mkdir data 2>nul
mkdir logs 2>nul
mkdir modules 2>nul

echo [4/4] Creating .env from template...
if not exist .env (
    copy .env.example .env
    echo .env file created! Open it and fill in your API keys.
) else (
    echo .env already exists — skipping.
)

echo.
echo ============================================
echo  Setup complete!
echo.
echo  NEXT STEPS:
echo  1. Open .env and fill in your API keys
echo  2. Run dry test:   python main.py --dry-run
echo  3. Run once:       python main.py --once
echo  4. Run scheduler:  python main.py --loop
echo  5. Dashboard:      open dashboard.html
echo ============================================
pause
