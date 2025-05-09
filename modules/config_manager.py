# X:\Aplikacje\dictaitor\modules\config_manager.py
import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Zdefiniuj ścieżkę do pliku konfiguracyjnego w folderze 'config'
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Główny katalog aplikacji
CONFIG_DIR = os.path.join(APP_DIR, "config")
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, "settings.json")

def ensure_config_dir_exists():
    """Upewnia się, że katalog 'config' istnieje."""
    if not os.path.exists(CONFIG_DIR):
        try:
            os.makedirs(CONFIG_DIR)
            logger.info(f"Utworzono katalog konfiguracyjny: {CONFIG_DIR}")
        except OSError as e:
            logger.error(f"Nie można utworzyć katalogu konfiguracyjnego {CONFIG_DIR}: {e}")
            # Można rzucić wyjątek, jeśli katalog jest krytyczny
            raise

def save_config(config_data: Dict[str, Any]) -> bool:
    """
    Zapisuje kompletną konfigurację do pliku JSON.
    
    Args:
        config_data: Dane konfiguracyjne do zapisania
        
    Returns:
        bool: True jeśli zapisano pomyślnie, False w przypadku błędu
    """
    ensure_config_dir_exists()
    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config_data, f, indent=4)
        logger.info(f"Konfiguracja zapisana w {CONFIG_FILE_PATH}")
        return True
    except IOError as e:
        logger.error(f"Błąd podczas zapisywania konfiguracji do {CONFIG_FILE_PATH}: {e}")
        return False
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd podczas zapisywania konfiguracji: {e}")
        return False

def load_config() -> Dict[str, Any]:
    """
    Wczytuje dane konfiguracyjne z pliku JSON.
    
    Returns:
        Dict[str, Any]: Słownik z konfiguracją lub pusty słownik jeśli nie ma pliku
    """
    ensure_config_dir_exists() # Upewnij się, że katalog istnieje nawet przy wczytywaniu
    if not os.path.exists(CONFIG_FILE_PATH):
        logger.warning(f"Plik konfiguracyjny {CONFIG_FILE_PATH} nie istnieje. Zwracam pustą konfigurację.")
        return {}  # Zwróć pusty słownik, jeśli plik nie istnieje
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
            logger.info(f"Konfiguracja wczytana z {CONFIG_FILE_PATH}")
            return config
    except json.JSONDecodeError as e:
        logger.error(f"Błąd dekodowania JSON w pliku {CONFIG_FILE_PATH}: {e}. Zwracam pustą konfigurację.")
        return {} # Zwróć pusty słownik w przypadku błędu formatu
    except IOError as e:
        logger.error(f"Błąd podczas wczytywania konfiguracji z {CONFIG_FILE_PATH}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd podczas wczytywania konfiguracji: {e}")
        return {}

def save_api_key(api_key: str) -> bool:
    """
    Zapisuje klucz API OpenRouter do pliku konfiguracyjnego.
    
    Args:
        api_key: Klucz API do zapisania
        
    Returns:
        bool: True jeśli zapisano pomyślnie, False w przypadku błędu
    """
    config = load_config() # Wczytaj istniejącą konfigurację
    config['openrouter_api_key'] = api_key
    return save_config(config)

def load_api_key() -> Optional[str]:
    """
    Wczytuje klucz API OpenRouter z pliku konfiguracyjnego.
    
    Returns:
        Optional[str]: Klucz API lub None, jeśli nie ma klucza
    """
    config = load_config()
    return config.get('openrouter_api_key')

# Funkcje do zapisywania i wczytywania klucza OpenAI API
def save_openai_api_key(api_key: str) -> bool:
    """
    Zapisuje klucz API OpenAI do pliku konfiguracyjnego.
    
    Args:
        api_key: Klucz API do zapisania
        
    Returns:
        bool: True jeśli zapisano pomyślnie, False w przypadku błędu
    """
    config = load_config()
    config['openai_api_key'] = api_key
    return save_config(config)

def load_openai_api_key() -> Optional[str]:
    """
    Wczytuje klucz API OpenAI z pliku konfiguracyjnego.
    
    Returns:
        Optional[str]: Klucz API lub None, jeśli nie ma klucza
    """
    config = load_config()
    return config.get('openai_api_key')

# Prosty test działania (można zakomentować po sprawdzeniu)
if __name__ == '__main__':
    ensure_config_dir_exists()
    print(f"Ścieżka do pliku konfiguracyjnego: {CONFIG_FILE_PATH}")
    
    # Test zapisywania i wczytywania klucza OpenRouter API
    test_key = "test_api_key_123"
    if save_api_key(test_key):
        print(f"Zapisano klucz OpenRouter: {test_key}")
        loaded_key = load_api_key()
        print(f"Odczytano klucz OpenRouter: {loaded_key}")
        if loaded_key == test_key:
            print("Test zapisu i odczytu klucza OpenRouter API powiódł się!")
        else:
            print("BŁĄD: Odczytany klucz różni się od zapisanego.")
    else:
        print("BŁĄD podczas zapisywania klucza OpenRouter API.")
        
    # Test zapisywania i wczytywania klucza OpenAI API
    test_openai_key = "test_openai_key_456"
    if save_openai_api_key(test_openai_key):
        print(f"Zapisano klucz OpenAI: {test_openai_key}")
        loaded_openai_key = load_openai_api_key()
        print(f"Odczytano klucz OpenAI: {loaded_openai_key}")
        if loaded_openai_key == test_openai_key:
            print("Test zapisu i odczytu klucza OpenAI API powiódł się!")
        else:
            print("BŁĄD: Odczytany klucz OpenAI różni się od zapisanego.")
    else:
        print("BŁĄD podczas zapisywania klucza OpenAI API.")
        
    # Test kompletnej konfiguracji
    test_config = {
        "openrouter_api_key": "test_router_key",
        "openai_api_key": "test_openai_key",
        "preferred_mode": "openai",
        "last_used_language": "pl"
    }
    
    if save_config(test_config):
        print("Zapisano pełną konfigurację")
        loaded_config = load_config()
        print(f"Odczytana konfiguracja: {loaded_config}")
        if loaded_config == test_config:
            print("Test zapisu i odczytu pełnej konfiguracji powiódł się!")
        else:
            print("BŁĄD: Odczytana konfiguracja różni się od zapisanej.")
    else:
        print("BŁĄD podczas zapisywania pełnej konfiguracji.")