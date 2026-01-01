@echo off
rem run_bot.bat - launch the bot and show incoming messages (foreground)
setlocal
set ROOT=%~dp0

rem Prefer virtualenv python if available
set VENV_PY=%ROOT%\.venv\Scripts\python.exe
if exist "%VENV_PY%" (
  echo Launching bot using virtualenv Python: %VENV_PY%
  set PYTHON=%VENV_PY%
  set ROOT_ENV=%ROOT%
  "%PYTHON%" -u -c "import os,sys,logging,runpy; os.environ['ROOT']=r'%%ROOT_ENV%%'; logging.basicConfig(level=logging.DEBUG,format='%%(asctime)s %%(name)s %%(levelname)s: %%(message)s'); logging.getLogger('telegram').setLevel(logging.DEBUG); logging.getLogger('telegram.ext').setLevel(logging.DEBUG); sys.path.insert(0, os.path.join(os.environ['ROOT'],'projects','bot')); runpy.run_path(os.path.join(os.environ['ROOT'],'projects','bot','python_bot','main.py'))"
  echo Bot finished. Press any key to close.
  pause >nul
  endlocal
  exit /b 0
)

rem If built exe exists, run it (will show console output if console build)
set EXE=%ROOT%dist\DBTeamV2_bot\DBTeamV2_bot.exe
if exist "%EXE%" (
  echo Executable found, launching: %EXE%
  "%EXE%" %*
  echo Executable finished. Press any key to close.
  pause >nul
  endlocal
  exit /b 0
)

rem Fallback: try system python
where python >nul 2>nul
if %errorlevel%==0 (
  echo Launching bot using system Python...
  python -u -c "import os,sys,logging,runpy; os.environ['ROOT']=r'%ROOT%'; logging.basicConfig(level=logging.DEBUG,format='%%(asctime)s %%(name)s %%(levelname)s: %%(message)s'); logging.getLogger('telegram').setLevel(logging.DEBUG); logging.getLogger('telegram.ext').setLevel(logging.DEBUG); sys.path.insert(0, os.path.join(os.environ['ROOT'],'projects','bot')); runpy.run_path(os.path.join(os.environ['ROOT'],'projects','bot','python_bot','main.py'))"
  echo Bot finished. Press any key to close.
  pause >nul
  endlocal
  exit /b 0
)

echo No virtualenv, exe, or python found. Build or create a .venv first.
pause >nul
endlocal
