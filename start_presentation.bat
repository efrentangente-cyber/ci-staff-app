@echo off
echo ============================================================
echo DCCCO CI STAFF APPLICATION - PRESENTATION MODE
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Fix database permissions
echo Fixing database permissions...
icacls app.db /grant Everyone:F >nul 2>&1

REM Check if app.db exists
if not exist app.db (
    echo ERROR: app.db not found!
    pause
    exit /b 1
)

REM Start the application
echo.
echo Starting application...
echo.
echo ============================================================
echo Application will start at: http://localhost:5000
echo.
echo Test Accounts:
echo   Admin:        admin@dccco.com / admin123
echo   Loan Officer: loan@dccco.com / loan123
echo   CI Staff:     ci@dccco.com / ci123
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

python app.py

pause
