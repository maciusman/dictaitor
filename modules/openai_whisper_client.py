# X:\Aplikacje\dictaitor\modules\openai_whisper_client.py
import requests
import os
import json
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class OpenAIWhisperClient:
    """Klient do komunikacji z API OpenAI Whisper dla transkrypcji audio."""
    
    API_URL = "https://api.openai.com/v1/audio/transcriptions"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicjalizuje klienta Whisper API.
        
        Args:
            api_key: Klucz API OpenAI
        """
        self.api_key = api_key
        self.debug_mode = False
    
    def update_api_key(self, api_key: str) -> bool:
        """
        Aktualizuje klucz API.
        
        Args:
            api_key: Nowy klucz API
            
        Returns:
            bool: True, jeśli aktualizacja się powiodła
        """
        if api_key and isinstance(api_key, str):
            self.api_key = api_key
            return True
        return False
    
    def transcribe_audio(self, audio_file_path: str, language: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Wykonuje transkrypcję pliku audio przy użyciu API OpenAI Whisper.
        
        Args:
            audio_file_path: Ścieżka do pliku audio
            language: Opcjonalny kod języka (np. "pl", "en")
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (transkrypcja, komunikat_błędu)
        """
        if not self.api_key:
            logger.error("Brak klucza API OpenAI")
            return None, "Brak klucza API OpenAI. Ustaw klucz API w konfiguracji."
        
        if not os.path.exists(audio_file_path):
            logger.error(f"Plik audio nie istnieje: {audio_file_path}")
            return None, f"Plik audio nie istnieje: {os.path.basename(audio_file_path)}"
            
        if self.debug_mode:
            file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
            logger.info(f"Informacje o pliku audio:")
            logger.info(f"- Ścieżka: {audio_file_path}")
            logger.info(f"- Rozmiar: {file_size_mb:.2f} MB")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Przygotowanie danych formularza
            data = {
                "model": "whisper-1",  # OpenAI ma tylko jeden model Whisper dostępny przez API
                "response_format": "text"
            }
            
            # Dodaj język, jeśli został określony
            if language:
                data["language"] = language
            
            # Otwórz plik audio do przesłania
            files = {
                "file": (os.path.basename(audio_file_path), open(audio_file_path, "rb"))
            }
            
            if self.debug_mode:
                logger.info(f"Wysyłanie żądania transkrypcji do API Whisper...")
                logger.info(f"URL API: {self.API_URL}")
                logger.info(f"Parametry: {data}")
            
            # Wyślij żądanie
            response = requests.post(
                self.API_URL,
                headers=headers,
                data=data,
                files=files,
                timeout=60
            )
            
            # Zamknij plik
            files["file"][1].close()
            
            if self.debug_mode:
                logger.info(f"Status odpowiedzi: {response.status_code}")
                try:
                    logger.info(f"Nagłówki odpowiedzi: {dict(response.headers)}")
                except:
                    pass
            
            # Sprawdź, czy żądanie się powiodło
            response.raise_for_status()
            
            # Transkrypcja może być zwrócona jako tekst lub JSON, w zależności od response_format
            content_type = response.headers.get("Content-Type", "")
            
            if "application/json" in content_type:
                result = response.json()
                if "text" in result:
                    return result["text"], None
                else:
                    logger.warning(f"Nieoczekiwany format odpowiedzi JSON: {json.dumps(result)}")
                    return json.dumps(result), None
            else:
                # Zwróć bezpośrednio tekst
                return response.text, None
                
        except requests.exceptions.RequestException as e:
            error_message = f"Błąd komunikacji z API OpenAI Whisper: {str(e)}"
            logger.error(error_message)
            
            # Spróbuj wyodrębnić więcej informacji o błędzie z odpowiedzi
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    if 'error' in error_data:
                        error_detail = error_data['error'].get('message', str(e))
                        error_message = f"Błąd API OpenAI: {error_detail}"
                except:
                    if hasattr(e, 'response') and hasattr(e.response, 'text'):
                        error_message = f"Błąd API ({e.response.status_code}): {e.response.text}"
            
            return None, error_message
            
        except Exception as e:
            error_message = f"Nieoczekiwany błąd podczas transkrypcji: {str(e)}"
            logger.error(error_message)
            return None, error_message
            
    def translate_audio_to_english(self, audio_file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Tłumaczy plik audio na język angielski przy użyciu API OpenAI Whisper.
        
        Args:
            audio_file_path: Ścieżka do pliku audio
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (przetłumaczony_tekst, komunikat_błędu)
        """
        if not self.api_key:
            logger.error("Brak klucza API OpenAI")
            return None, "Brak klucza API OpenAI. Ustaw klucz API w konfiguracji."
        
        if not os.path.exists(audio_file_path):
            logger.error(f"Plik audio nie istnieje: {audio_file_path}")
            return None, f"Plik audio nie istnieje: {os.path.basename(audio_file_path)}"
            
        if self.debug_mode:
            file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
            logger.info(f"Informacje o pliku audio (tłumaczenie):")
            logger.info(f"- Ścieżka: {audio_file_path}")
            logger.info(f"- Rozmiar: {file_size_mb:.2f} MB")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Przygotowanie danych formularza
            data = {
                "model": "whisper-1",  # OpenAI ma tylko jeden model Whisper dostępny przez API
                "response_format": "text" 
            }
            
            # Otwórz plik audio do przesłania
            files = {
                "file": (os.path.basename(audio_file_path), open(audio_file_path, "rb"))
            }
            
            translation_api_url = "https://api.openai.com/v1/audio/translations"

            if self.debug_mode:
                logger.info(f"Wysyłanie żądania tłumaczenia do API Whisper...")
                logger.info(f"URL API: {translation_api_url}")
                logger.info(f"Parametry: {data}")
            
            # Wyślij żądanie
            response = requests.post(
                translation_api_url,
                headers=headers,
                data=data,
                files=files,
                timeout=60 
            )
            
            # Zamknij plik
            files["file"][1].close()
            
            if self.debug_mode:
                logger.info(f"Status odpowiedzi: {response.status_code}")
                try:
                    logger.info(f"Nagłówki odpowiedzi: {dict(response.headers)}")
                except:
                    pass
            
            # Sprawdź, czy żądanie się powiodło
            response.raise_for_status()
            
            content_type = response.headers.get("Content-Type", "")
            
            if "application/json" in content_type:
                result = response.json()
                if "text" in result:
                    return result["text"], None
                else:
                    logger.warning(f"Nieoczekiwany format odpowiedzi JSON: {json.dumps(result)}")
                    return json.dumps(result), None
            else:
                # Zwróć bezpośrednio tekst
                return response.text, None
                
        except requests.exceptions.RequestException as e:
            error_message = f"Błąd komunikacji z API OpenAI Whisper (tłumaczenie): {str(e)}"
            logger.error(error_message)
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    if 'error' in error_data:
                        error_detail = error_data['error'].get('message', str(e))
                        error_message = f"Błąd API OpenAI (tłumaczenie): {error_detail}"
                except:
                    if hasattr(e, 'response') and hasattr(e.response, 'text'):
                        error_message = f"Błąd API ({e.response.status_code}) (tłumaczenie): {e.response.text}"
            
            return None, error_message
            
        except Exception as e:
            error_message = f"Nieoczekiwany błąd podczas tłumaczenia: {str(e)}"
            logger.error(error_message)
            return None, error_message