@echo off
echo Uruchamianie aplikacji DictAItor...
echo.

REM Użyj ścieżki do folderu, w którym znajduje się ten skrypt
cd /d %~dp0

REM Sprawdź czy Python jest zainstalowany
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo BŁĄD: Python nie jest zainstalowany lub nie jest dostępny w ścieżce PATH.
    echo Zainstaluj Python ze strony https://www.python.org/downloads/
    echo Upewnij się, że zaznaczyłeś opcję "Add Python to PATH" podczas instalacji.
    echo.
    pause
    exit /b 1
)

REM Uruchom aplikację
python main_app.py

REM Jeśli aplikacja zakończy się z błędem, nie zamykaj okna
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Aplikacja zakończyła działanie z błędem.
    pause
)