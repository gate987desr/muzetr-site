@echo off
cd /d "%~dp0"
where git >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Git is not installed or not in PATH.
  echo.
  pause
  exit /b 1
)
if not exist ".git" (
  echo.
  echo   This folder is not a Git repository.
  echo.
  pause
  exit /b 1
)
echo.
echo   [1/2] Building the site locally...
python build.py
if errorlevel 1 (
  pause
  exit /b 1
)
echo.
echo   [2/2] Committing and pushing to GitHub...
git add -A
git commit -m "update site" || echo   Nothing changed, skipping commit.
git push
echo.
echo   Pushed. Netlify will rebuild in about a minute.
pause
