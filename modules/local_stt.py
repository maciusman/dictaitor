# X:\Aplikacje\dictaitor\modules\local_stt.py
import os
import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

# Dostępne modele Whisper (od najmniejszego/najszybszego do największego/najdokładniejszego)
# Dodano model 'turbo', który jest szybszy niż 'large' i bardzo dokładny
AVAILABLE_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "turbo"]

# Globalna zmienna do przechowywania załadowanego modelu, aby nie ładować go wielokrotnie
_loaded_model = None
_current_model_name = None

# Sprawdź czy Whisper jest dostępny i które modele są zainstalowane
try:
    import whisper
    
    # Sprawdź czy model turbo jest dostępny w zainstalowanej wersji
    try:
        whisper_available_models = whisper.available_models()
        if "turbo" not in whisper_available_models and "turbo" in AVAILABLE_WHISPER_MODELS:
            logger.info("Model 'turbo' nie jest dostępny w tej wersji Whisper. Dostępne modele: " + ", ".join(whisper_available_models))
            # Możemy tutaj zaktualizować listę dostępnych modeli, usuwając te niedostępne
            AVAILABLE_WHISPER_MODELS = [model for model in AVAILABLE_WHISPER_MODELS if model in whisper_available_models]
    except Exception as e:
        logger.warning(f"Nie można pobrać listy dostępnych modeli Whisper: {e}")
    
    WHISPER_INSTALLED = True
    logger.info("Biblioteka Whisper jest dostępna. Dostępne modele: " + ", ".join(AVAILABLE_WHISPER_MODELS))
except ImportError as e:
    WHISPER_INSTALLED = False
    logger.warning(f"Biblioteka Whisper nie jest zainstalowana. Lokalna transkrypcja nie będzie dostępna. Błąd: {str(e)}")

def load_whisper_model(model_name: str = "base"):
    """
    Ładuje określony model Whisper.
    Ponowne wywołanie z tą samą nazwą modelu nie będzie go ładować ponownie.
    """
    global _loaded_model, _current_model_name
    
    if not WHISPER_INSTALLED:
        logger.error("Próba załadowania modelu Whisper, ale biblioteka nie jest zainstalowana")
        return None
        
    if _loaded_model is not None and _current_model_name == model_name:
        logger.info(f"Model Whisper '{model_name}' jest już załadowany.")
        return _loaded_model
    
    if model_name not in AVAILABLE_WHISPER_MODELS:
        logger.error(f"Nieznany model Whisper: {model_name}. Dostępne: {AVAILABLE_WHISPER_MODELS}")
        # Jeżeli model "turbo" jest dostępny, użyj go jako domyślnego
        if "turbo" in AVAILABLE_WHISPER_MODELS:
            model_name = "turbo"
            logger.warning(f"Używam modelu Whisper: '{model_name}'")
        else:
            # W przeciwnym razie użyj "base" jako bezpiecznej opcji
            model_name = "base" 
            logger.warning(f"Używam domyślnego modelu Whisper: '{model_name}'")

    try:
        logger.info(f"Ładowanie modelu Whisper: '{model_name}'... To może chwilę potrwać przy pierwszym uruchomieniu.")
        # Modele są pobierane automatycznie przy pierwszym użyciu i cache'owane
        # Domyślny katalog cache: ~/.cache/whisper
        _loaded_model = whisper.load_model(model_name)
        _current_model_name = model_name
        logger.info(f"Model Whisper '{model_name}' załadowany pomyślnie.")
        return _loaded_model
    except Exception as e:
        logger.error(f"Nie udało się załadować modelu Whisper '{model_name}': {e}")
        _loaded_model = None # Zresetuj w przypadku błędu
        _current_model_name = None
        return None

def get_available_models() -> List[str]:
    """
    Sprawdza, które modele Whisper są faktycznie dostępne lokalnie.
    
    Returns:
        List[str]: Lista dostępnych modeli
    """
    if not WHISPER_INSTALLED:
        return []
        
    try:
        return whisper.available_models()
    except Exception as e:
        logger.error(f"Błąd podczas pobierania dostępnych modeli: {e}")
        return AVAILABLE_WHISPER_MODELS

def normalize_path(path: str) -> str:
    """
    Normalizuje ścieżkę pliku, aby była kompatybilna z Whisper na Windows.
    
    Args:
        path (str): Ścieżka do znormalizowania
        
    Returns:
        str: Znormalizowana ścieżka
    """
    # Zamień ukośniki w ścieżce na te odpowiednie dla systemu
    normalized_path = os.path.abspath(os.path.normpath(path))
    
    # Na wszelki wypadek sprawdź, czy plik istnieje
    if not os.path.exists(normalized_path):
        logger.error(f"Plik nie istnieje: {normalized_path} (oryginalnie: {path})")
        raise FileNotFoundError(f"Plik nie istnieje: {normalized_path} (oryginalnie: {path})")
        
    # Dodatkowe logowanie
    logger.info(f"Plik zweryfikowany - istnieje: {normalized_path}")
    return normalized_path

def transcribe_audio_local(audio_file_path: str, model_name: str = "turbo", language: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Przeprowadza transkrypcję pliku audio przy użyciu lokalnego modelu Whisper.

    Args:
        audio_file_path (str): Ścieżka do pliku audio.
        model_name (str): Nazwa modelu Whisper do użycia (np. "tiny", "base", "turbo").
        language (Optional[str]): Kod języka (np. "en", "pl") do transkrypcji. 
                                 Jeśli None, Whisper spróbuje wykryć automatycznie.

    Returns:
        Tuple[Optional[str], Optional[str]]: (transkrypcja, błąd_wiadomość)
    """
    if not WHISPER_INSTALLED:
        return None, "Biblioteka Whisper nie jest zainstalowana. Zainstaluj używając: pip install openai-whisper"
        
    try:
        # Normalizuj ścieżkę do pliku
        normalized_path = normalize_path(audio_file_path)
        
        # Dodatkowe logowanie
        logger.info(f"Ścieżka znormalizowana: {normalized_path}")
        logger.info(f"Rozmiar pliku: {os.path.getsize(normalized_path) / 1024:.2f} KB")
        
        model = load_whisper_model(model_name)
        if model is None:
            return None, f"Nie udało się załadować modelu Whisper '{model_name}'."

        logger.info(f"Rozpoczynanie lokalnej transkrypcji pliku: {normalized_path} (model: {model_name}, język: {language or 'auto'})")
        
        # Opcje transkrypcji
        transcribe_options = {"fp16": False} # Ustaw na True, jeśli masz GPU NVIDII i CUDA
        if language:
            transcribe_options["language"] = language
        
        # Sprawdź jeszcze raz przed przekazaniem do Whisper
        if not os.path.exists(normalized_path):
            raise FileNotFoundError(f"Plik zniknął przed transkrypcją: {normalized_path}")
            
        # Spróbuj alternatywne podejście z wczytywaniem przez librosa, jeśli jest dostępne
        try:
            import librosa
            logger.info("Wczytywanie pliku audio przez librosa")
            audio, sr = librosa.load(normalized_path, sr=16000, mono=True)
            # Użyj metody transcribe na tablicy audio
            result = model.transcribe(audio, **transcribe_options)
        except ImportError:
            # Jeśli nie ma librosa, użyj standardowej metody
            logger.info("Użycie standardowej metody wczytywania audio")
            result = model.transcribe(normalized_path, **transcribe_options)
        except Exception as e:
            # W przypadku błędu wczytywania przez librosa, użyj standardowej metody
            logger.warning(f"Błąd wczytywania przez librosa: {e}, próbuję standardową metodę")
            result = model.transcribe(normalized_path, **transcribe_options)
        
        transcription = result["text"]
        
        detected_lang = result.get("language", "nie wykryto")
        logger.info(f"Lokalna transkrypcja zakończona. Wykryty język: {detected_lang}.")
        return transcription.strip(), None
        
    except FileNotFoundError as e:
        error_msg = f"Nie można znaleźć pliku audio: {e}"
        logger.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Błąd podczas lokalnej transkrypcji pliku {audio_file_path}: {e}"
        logger.error(error_msg)
        return None, error_msg