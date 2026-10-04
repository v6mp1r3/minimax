@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo        DocuGuide - local demo
echo ==========================================

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo.
  echo [!] Am creat .env din .env.example.
  echo [!] Pentru Gemini: deschide .env si pune GEMINI_API_KEY=...
  echo [!] Pentru testare este necesara o cheie Gemini. Ollama este optional si nu porneste automat.
  echo.
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating Python environment...
  py -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Python nu a fost gasit. Instaleaza Python 3.11+ si bifeaza Add Python to PATH.
    pause
    exit /b 1
  )
)

if not exist "frontend\node_modules" (
  echo Installing frontend dependencies...
  pushd frontend
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install a esuat.
    popd
    pause
    exit /b 1
  )
  popd
)

call .venv\Scripts\activate
python -m pip install -r backend\requirements.txt

if errorlevel 1 (
  echo [ERROR] Instalarea dependintelor Python a esuat.
  pause
  exit /b 1
)

echo.
echo Building frontend...
pushd frontend
call npm run build
if errorlevel 1 (
  echo [ERROR] Build frontend a esuat.
  popd
  pause
  exit /b 1
)
popd

echo.
echo ==========================================
echo Starting DocuGuide...
echo Open:   http://127.0.0.1:8000
echo Health: http://127.0.0.1:8000/api/health
echo ==========================================
echo.

uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
