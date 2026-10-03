@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating Python environment...
  py -m venv .venv
)

if not exist "frontend\dist\index.html" (
  echo Building frontend...
  pushd frontend
  call npm install
  call npm run build
  popd
)

call .venv\Scripts\activate
python -m pip install -r backend\requirements.txt

echo.
echo Starting DocuGuide...
echo Open http://127.0.0.1:8000
echo Health: http://127.0.0.1:8000/api/health
echo.
uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
