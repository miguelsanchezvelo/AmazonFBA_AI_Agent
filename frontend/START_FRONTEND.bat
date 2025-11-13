@echo off
echo ========================================
echo  Amazon FBA Frontend - Starting...
echo ========================================
echo.

cd "%~dp0"

echo [1/2] Installing dependencies...
call npm install

echo.
echo [2/2] Starting development server...
echo.
echo Frontend will be available at: http://localhost:5173
echo.
echo Press Ctrl+C to stop the server
echo.

call npm run dev

pause

