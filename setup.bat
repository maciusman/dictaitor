@echo off
echo ========================================
echo     Instalacja DictAItor v0.3.0
echo ========================================
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

echo Instalacja wymaganych bibliotek...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo BŁĄD: Nie udało się zainstalować wymaganych bibliotek.
    echo Sprawdź połączenie z internetem i uprawnienia.
    pause
    exit /b 1
)

echo.
echo Pobieranie modelu Whisper (tylko przy pierwszym uruchomieniu)...
echo To może potrwać kilka minut, w zależności od prędkości internetu.
echo.
python -c "import whisper; whisper.load_model('base')"

echo.
echo ========================================
echo Instalacja zakończona pomyślnie!
echo.
echo Aby uruchomić aplikację, kliknij dwukrotnie na plik run_dictaitor.bat
echo ========================================
echo.
pause