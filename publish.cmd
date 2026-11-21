@echo off
cd /d "%~dp0"
where git >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Git is not installed. Download: https://git-scm.com/download/win
  echo.
  pause
  exit /b 1
)
if not exist ".git" (
  echo.
  echo   This folder is not a Git repository yet.
  echo   Run these once inside this folder:
  echo.
  echo     git init
  echo     git remote add origin YOUR_REPO_URL
  echo     git branch -M main
  echo.
  pause
  exit /b 1
)
python build.py
if errorlevel 1 (
  pause
  exit /b 1
)
git add -A
git commit -m "update site"
git push
pause
