# X:\Aplikacje\dictaitor\modules\audio_recorder.py
import pyaudio
import wave
import threading
import time
import os
import logging

logger = logging.getLogger(__name__)

# Domyślny katalog na nagrania (np. podkatalog w głównym folderze aplikacji)
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDINGS_DIR = os.path.join(APP_DIR, "recordings")


class AudioRecorder:
    def __init__(self, filename_prefix="recording", 
                 # Zoptymalizowane parametry nagrywania
                 rate=16000,     # Zmniejszono z domyślnego 44100/48000 do 16kHz 
                 channels=1,     # Mono zamiast stereo
                 chunk_size=1024,
                 sample_width=2  # 16-bit, optymalny dla rozpoznawania mowy
                ):
        self.filename_prefix = filename_prefix
        self.filepath = "" # Pełna ścieżka do pliku zostanie ustawiona przy starcie nagrywania
        self.rate = rate
        self.channels = channels
        self.format = pyaudio.paInt16  # 16-bit PCM (odpowiada sample_width=2)
        self.chunk_size = chunk_size
        self.sample_width = sample_width
        
        self.audio_interface = None
        self.stream = None
        self.frames = []
        self.is_recording = False
        self.recording_thread = None

        self._ensure_recordings_dir_exists()
        logger.info(f"Inicjalizacja AudioRecorder z parametrami: {rate}Hz, {channels} kanał(y), {sample_width*8}-bit")

    def _ensure_recordings_dir_exists(self):
        """Upewnia się, że katalog na nagrania istnieje."""
        if not os.path.exists(RECORDINGS_DIR):
            try:
                os.makedirs(RECORDINGS_DIR)
                logger.info(f"Utworzono katalog na nagrania: {RECORDINGS_DIR}")
            except OSError as e:
                logger.error(f"Nie można utworzyć katalogu na nagrania {RECORDINGS_DIR}: {e}")
                # Można rzucić wyjątek, jeśli to krytyczne

    def _get_unique_filename(self) -> str:
        """Generuje unikalną nazwę pliku dla nagrania."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{self.filename_prefix}_{timestamp}.wav"
        return os.path.join(RECORDINGS_DIR, filename)

    def start_recording(self):
        if self.is_recording:
            logger.warning("Próba rozpoczęcia nagrywania, gdy już jest aktywne.")
            return False

        try:
            self.audio_interface = pyaudio.PyAudio()
            self.stream = self.audio_interface.open(format=self.format,
                                                  channels=self.channels,
                                                  rate=self.rate,
                                                  input=True,
                                                  frames_per_buffer=self.chunk_size)
        except Exception as e:
            logger.error(f"Nie można otworzyć strumienia audio: {e}")
            if self.audio_interface:
                self.audio_interface.terminate()
                self.audio_interface = None
            return False # Nie udało się rozpocząć

        self.filepath = self._get_unique_filename() # Ustaw ścieżkę pliku
        self.is_recording = True
        self.frames = []
        self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.recording_thread.start()
        logger.info(f"Rozpoczęto nagrywanie. Plik: {self.filepath}")
        return True

    def _record_loop(self):
        logger.debug("Pętla nagrywania uruchomiona.")
        while self.is_recording:
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                self.frames.append(data)
            except IOError as e: # Np. odłączenie mikrofonu
                logger.error(f"Błąd wejścia/wyjścia podczas nagrywania: {e}")
                self.is_recording = False # Przerwij pętlę w przypadku błędu IO
                break 
            except Exception as e:
                logger.error(f"Nieoczekiwany błąd w pętli nagrywania: {e}")
                # Rozważ czy przerwać pętlę, czy próbować kontynuować
                self.is_recording = False 
                break
        logger.debug("Pętla nagrywania zakończona.")
        self._cleanup_stream()

    def stop_recording(self) -> str | None:
        if not self.is_recording:
            logger.warning("Próba zatrzymania nagrywania, gdy nie jest aktywne.")
            return None

        self.is_recording = False # Sygnał dla pętli nagrywania, aby się zakończyła
        
        if self.recording_thread and self.recording_thread.is_alive():
            logger.debug("Oczekiwanie na zakończenie wątku nagrywania...")
            self.recording_thread.join(timeout=2) # Dajmy wątkowi chwilę na zakończenie
            if self.recording_thread.is_alive():
                logger.warning("Wątek nagrywania nie zakończył się w oczekiwanym czasie.")

        self._cleanup_stream() # Upewnij się, że strumień jest zamknięty

        if self.audio_interface:
            self.audio_interface.terminate()
            self.audio_interface = None
            logger.debug("Zakończono interfejs PyAudio.")

        if not self.frames:
            logger.warning("Brak klatek audio do zapisania.")
            return None

        return self._save_to_file()

    def _cleanup_stream(self):
        if self.stream and self.stream.is_active(): # Sprawdź czy strumień jest aktywny
            try:
                self.stream.stop_stream()
                logger.debug("Strumień audio zatrzymany.")
            except Exception as e:
                logger.error(f"Błąd podczas zatrzymywania strumienia: {e}")
        if self.stream:
            try:
                self.stream.close()
                logger.debug("Strumień audio zamknięty.")
            except Exception as e:
                logger.error(f"Błąd podczas zamykania strumienia: {e}")
        self.stream = None


    def _save_to_file(self) -> str | None:
        if not self.frames:
            logger.warning("Brak klatek do zapisania (frames).")
            return None
        if not self.filepath:
            logger.error("Ścieżka pliku nie została ustawiona przed zapisem.")
            return None

        try:
            wf = wave.open(self.filepath, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.sample_width)  # Używamy ustawionej wartości zamiast pobierania przez PyAudio
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            
            # Logowanie informacji o rozmiarze pliku
            file_size_bytes = os.path.getsize(self.filepath)
            file_size_mb = file_size_bytes / (1024 * 1024)
            logger.info(f"Nagranie zapisano jako {self.filepath} (rozmiar: {file_size_mb:.2f} MB)")
            
            # Oblicz długość nagrania w sekundach
            frames_count = len(b''.join(self.frames)) / (self.channels * self.sample_width)
            duration_seconds = frames_count / self.rate
            logger.info(f"Długość nagrania: {duration_seconds:.2f} sekund")
            
            return self.filepath
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania pliku WAV {self.filepath}: {e}")
            return None

    def is_active(self) -> bool:
        return self.is_recording