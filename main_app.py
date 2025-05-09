# X:\Aplikacje\dictaitor\main_app.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import logging
from functools import partial
from typing import Optional, Tuple, List, Dict, Any, Callable

# Importy z naszych modułów
from modules.config_manager import save_config, load_config
from modules.audio_recorder import AudioRecorder
# Usunięto import OpenRouterClient

# Konfiguracja logowania z lepszą organizacją
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("DictAItorApp")

# Sprawdźmy dostępność biblioteki OpenAI Whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
    # Próbuj zaimportować moduł local_stt
    try:
        from modules.local_stt import transcribe_audio_local, AVAILABLE_WHISPER_MODELS, get_available_models
        LOCAL_STT_MODULE_AVAILABLE = True
        
        # Pobierz faktycznie dostępne modele z Whisper
        actual_models = get_available_models()
        if actual_models:
            AVAILABLE_WHISPER_MODELS = actual_models
            logger.info(f"Pobrano dostępne modele Whisper: {', '.join(AVAILABLE_WHISPER_MODELS)}")
    except ImportError as e:
        # Jeśli moduł local_stt nie jest dostępny, ale whisper tak, to definiujemy podstawową listę modeli
        LOCAL_STT_MODULE_AVAILABLE = False
        AVAILABLE_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
        logger.warning(f"Nie można zaimportować modułu local_stt: {str(e)}")
        
        # Sprawdź czy model turbo jest dostępny
        try:
            if "turbo" in whisper.available_models():
                AVAILABLE_WHISPER_MODELS.append("turbo")
                logger.info("Model 'turbo' jest dostępny w Whisper!")
        except Exception as e:
            logger.warning(f"Nie można sprawdzić dostępności modelu 'turbo': {str(e)}")
except ImportError as e:
    WHISPER_AVAILABLE = False
    LOCAL_STT_MODULE_AVAILABLE = False
    AVAILABLE_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large", "turbo"]
    logger.warning(f"Nie można zaimportować biblioteki Whisper: {str(e)}")

# Sprawdźmy dostępność klienta OpenAI API
try:
    from modules.openai_whisper_client import OpenAIWhisperClient
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Użyjemy Pillow do obsługi obrazów PNG (dla logo)
from PIL import Image, ImageTk

# Stałe aplikacji wydzielone jako globalne zmienne dla łatwiejszej konfiguracji
APP_NAME = "DictAItor"
APP_VERSION = "0.3.0"  # Zaktualizowano wersję
WINDOW_WIDTH = 700
WINDOW_HEIGHT = 750  # Powiększono okno dla dodatkowych kontrolek

# Ścieżki
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(CURRENT_DIR, "assets")
CONFIG_DIR = os.path.join(CURRENT_DIR, "config")
RECORDINGS_DIR = os.path.join(CURRENT_DIR, "recordings")
LOGO_FILE = os.path.join(ASSETS_DIR, "logo.png")

# Klucze konfiguracji
OPENROUTER_KEY_CONFIG = 'openrouter_api_key'  # Zachowane dla kompatybilności
OPENAI_KEY_CONFIG = 'openai_api_key'
PREFERRED_MODE_CONFIG = 'preferred_mode'
PREFERRED_MODEL_CONFIG = 'preferred_model'
PREFERRED_LANGUAGE_CONFIG = 'preferred_language'

# Upewnij się, że niezbędne katalogi istnieją
for directory in [ASSETS_DIR, CONFIG_DIR, RECORDINGS_DIR]:
    os.makedirs(directory, exist_ok=True)

class DictAItorApp:
    """
    Główna klasa aplikacji DictAItor, która zarządza interfejsem użytkownika
    i funkcjonalnością transkrypcji mowy na tekst.
    """
    def __init__(self, root: tk.Tk) -> None:
        """
        Inicjalizuje aplikację.
        
        Args:
            root: Główne okno Tkinter
        """
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        # Zmienione na True, True aby umożliwić skalowanie
        self.root.resizable(True, True)
        
        # Ustawienie minimalnego rozmiaru okna
        self.root.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Wczytywanie konfiguracji
        self.config = load_config()
        
        # Inicjalizacja modułów
        self.api_key_value = self.config.get(OPENROUTER_KEY_CONFIG, '')
        self.openai_key_value = self.config.get(OPENAI_KEY_CONFIG, '')
        self.recorder = AudioRecorder()
        
        # Inicjalizacja klienta OpenAI Whisper
        if OPENAI_AVAILABLE:
            self.openai_client = OpenAIWhisperClient(api_key=self.openai_key_value)
            self.openai_client.debug_mode = True  # Włącz tryb debugowania
        
        # Zmienne stanu
        self.is_recording_app_state = False
        self.selected_whisper_model = tk.StringVar()  # Model Whisper do lokalnej transkrypcji
        self.selected_language_code = tk.StringVar()  # Kod języka dla transkrypcji (opcjonalnie)
        self.file_path_var = tk.StringVar()  # Ścieżka do wybranego pliku audio
        
        # Ustaw domyślny język z konfiguracji lub pusty
        self.selected_language_code.set(self.config.get(PREFERRED_LANGUAGE_CONFIG, ''))
        
        # Ustaw domyślny model Whisper - preferuj "turbo" jeśli jest dostępny
        preferred_model = self.config.get(PREFERRED_MODEL_CONFIG, '')
        if preferred_model and preferred_model in AVAILABLE_WHISPER_MODELS:
            self.selected_whisper_model.set(preferred_model)
        elif "turbo" in AVAILABLE_WHISPER_MODELS:
            self.selected_whisper_model.set("turbo")  # Preferuj model turbo
        elif AVAILABLE_WHISPER_MODELS:
            self.selected_whisper_model.set(AVAILABLE_WHISPER_MODELS[1] if len(AVAILABLE_WHISPER_MODELS) > 1 else AVAILABLE_WHISPER_MODELS[0])
        
        # Tryb transkrypcji - wybierz na podstawie konfiguracji lub dostępności
        preferred_mode = self.config.get(PREFERRED_MODE_CONFIG, '')
        
        if preferred_mode == 'local' and WHISPER_AVAILABLE:
            self.transcription_mode = tk.StringVar(value="local")
        elif preferred_mode == 'openai' and OPENAI_AVAILABLE:
            self.transcription_mode = tk.StringVar(value="openai")
        else:
            # Domyślnie wybierz lokalną transkrypcję jeśli dostępna
            if WHISPER_AVAILABLE:
                self.transcription_mode = tk.StringVar(value="local")
            elif OPENAI_AVAILABLE:
                self.transcription_mode = tk.StringVar(value="openai")
            else:
                self.transcription_mode = tk.StringVar(value="local")
                
        self.last_recorded_file = None

        # Cache dla komponentów GUI
        self._widgets = {}

        # Ustawienia stylu ttk
        self._setup_ttk_style()
        
        # Tworzenie interfejsu
        self._create_widgets()
        self._load_initial_config()
        
        # Ustawienie propagacji wielkości głównego okna
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Pokaż informacje o dostępności usług
        self._show_service_status()

    def _show_service_status(self):
        """Wyświetla informacje o dostępności usług transkrypcji."""
        status_messages = []
        
        if WHISPER_AVAILABLE:
            if "turbo" in AVAILABLE_WHISPER_MODELS:
                status_messages.append("✅ Whisper model 'turbo' jest dostępny (8x szybszy niż 'large')")
            else:
                status_messages.append("✅ Lokalna transkrypcja Whisper jest dostępna")
        else:
            status_messages.append("❌ Lokalna transkrypcja Whisper jest niedostępna (brak biblioteki)")
        
        if not OPENAI_AVAILABLE:
            status_messages.append("❌ Moduł OpenAI Whisper API nie jest zaimplementowany")
        elif not self.openai_key_value:
            status_messages.append("⚠️ Brak klucza API OpenAI (skonfiguruj w sekcji OpenAI API)")
        else:
            status_messages.append("✅ OpenAI Whisper API jest dostępne")
        
        if status_messages:
            self.root.after(800, lambda: messagebox.showinfo(
                "Status Usług Transkrypcji", 
                "Status usług transkrypcji:\n\n" + "\n".join(status_messages)
            ))

    def _setup_ttk_style(self) -> None:
        """Konfiguruje styl dla widgetów ttk."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Ustawienia ciemnego motywu ze zmienionym kolorem tła
        bg_color = "#151515"  # Dokładny kolor tła, który został podany
        fg_color = "#e0e0e0"  # Jasny tekst
        selected_bg = "#252525"  # Nieco jaśniejsze tło dla zaznaczonych elementów
        accent_color = "#444444"  # Kolor akcentów
        accent_blue = "#3a7ebf"  # Niebieski akcent dla przycisków
        
        # Główne ustawienia
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        
        # Stylizacja przycisków - dodajemy akcenty kolorystyczne
        style.configure('TButton', 
                       background=accent_blue, 
                       foreground="white", 
                       padding=6,
                       font=('Arial', 9, 'bold'))
        style.map('TButton', 
                 background=[('active', "#4a8ecf"), ('pressed', "#2a6eaf")],
                 foreground=[('active', "white"), ('pressed', "white")])
        
        # Przyciski akcji z innym kolorem
        style.configure('Action.TButton', 
                      background="#2c8057", 
                      foreground="white")
        style.map('Action.TButton', 
                 background=[('active', "#35996a"), ('pressed', "#246c4a")],
                 foreground=[('active', "white"), ('pressed', "white")])
        
        # Konfiguracja stylów dla pozostałych elementów
        style.configure('TLabelframe', background=bg_color, foreground=fg_color)
        style.configure('TLabelframe.Label', background=bg_color, foreground=fg_color, font=('Arial', 9, 'bold'))
        
        style.configure('TRadiobutton', background=bg_color, foreground=fg_color, padding=2)
        style.map('TRadiobutton', 
                 background=[('active', bg_color), ('selected', bg_color)],
                 foreground=[('active', fg_color), ('selected', fg_color)])
        
        style.configure('TCombobox', 
                      fieldbackground=bg_color, 
                      background=accent_color, 
                      foreground=fg_color,
                      arrowcolor=fg_color)
        style.map('TCombobox', 
                 fieldbackground=[('readonly', bg_color)],
                 background=[('readonly', accent_color)],
                 foreground=[('readonly', fg_color)])
        
        style.configure('TEntry', 
                      fieldbackground=bg_color, 
                      foreground=fg_color,
                      insertcolor=fg_color)
        
        # Ustawienie dla ramek LabelFrame
        style.configure('TLabelframe', background=bg_color, foreground=fg_color)
        style.configure('TLabelframe.Label', background=bg_color, foreground=fg_color)

        # Dostosowanie głównego okna
        self.root.configure(background=bg_color)

    def _load_initial_config(self) -> None:
        """Wczytuje początkową konfigurację aplikacji."""
        # Ustaw klucz OpenAI jeśli jest dostępny
        if hasattr(self, 'openai_api_entry') and self.openai_key_value:
            self.openai_api_entry.insert(0, self.openai_key_value)

    def _create_widgets(self) -> None:
        """Tworzy wszystkie widgety interfejsu użytkownika."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_header(main_frame)
        self._create_api_section(main_frame)
        
        if OPENAI_AVAILABLE:
            self._create_openai_api_section(main_frame)
            
        self._create_transcription_mode_section(main_frame)
        self._create_model_section(main_frame)
        self._create_action_section(main_frame)
        self._create_file_selection_section(main_frame)
        self._create_transcription_section(main_frame)
        
        # Aktualizacja trybów i widoczności komponentów - teraz po utworzeniu wszystkich widgetów
        self.root.after(100, self._update_transcription_mode)

    def _create_header(self, parent: ttk.Frame) -> None:
        """
        Tworzy sekcję nagłówka z logo.
        
        Args:
            parent: Widget rodzica
        """
        header_frame = ttk.Frame(parent)
        header_frame.pack(pady=(5, 15), fill=tk.X)
        
        # Ładowanie logo
        try:
            if os.path.exists(LOGO_FILE):
                img = Image.open(LOGO_FILE)
                # Zwiększamy maksymalną wysokość logo
                max_logo_height = 120  # Zwiększono z 80 na 120
                
                # Obliczamy nowe wymiary, zachowując proporcje
                img_ratio = img.width / img.height
                new_height = min(img.height, max_logo_height)
                new_width = int(new_height * img_ratio)
                
                # Przy większych logo możemy chcieć zwiększyć szerokość
                # w stosunku do wysokości dla lepszego efektu wizualnego
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                self.logo_image = ImageTk.PhotoImage(img)
                
                # Tworzymy kontener dla logo, który będzie wycentrowany
                logo_container = ttk.Frame(header_frame)
                logo_container.pack(fill=tk.X)
                
                # Umieszczamy logo na środku
                logo_label = ttk.Label(logo_container, image=self.logo_image)
                logo_label.pack(pady=10)  # Dodajemy pionowy padding
                
                # Dodajemy przestrzeń po logo
                ttk.Frame(header_frame, height=5).pack(fill=tk.X)
            else:
                logger.warning(f"Plik logo nie znaleziony: {LOGO_FILE}")
        except Exception as e:
            logger.error(f"Błąd ładowania logo: {e}")

    def _create_api_section(self, parent: ttk.Frame) -> None:
        """
        Tworzy sekcję konfiguracji API OpenAI.
        
        Args:
            parent: Widget rodzica
        """
        # Kompletnie pomijamy tę metodę, wszystko jest w _create_openai_api_section
        pass

    def _create_openai_api_section(self, parent: ttk.Frame) -> None:
        """
        Tworzy sekcję konfiguracji API OpenAI.
        
        Args:
            parent: Widget rodzica
        """
        api_frame = ttk.LabelFrame(parent, text="Konfiguracja OpenAI API (dla transkrypcji online)", padding="10")
        api_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(api_frame, text="Klucz API:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.openai_api_entry = ttk.Entry(api_frame, width=50, show="*")
        self.openai_api_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        save_key_button = ttk.Button(api_frame, text="🔑 Zapisz Klucz", command=self.save_openai_key_action)
        save_key_button.grid(row=0, column=2, padx=5, pady=5)
        
        api_frame.columnconfigure(1, weight=1)
    
    def _create_transcription_mode_section(self, parent: ttk.Frame) -> None:
        """
        Tworzy sekcję wyboru trybu transkrypcji.
        
        Args:
            parent: Widget rodzica
        """
        mode_frame = ttk.LabelFrame(parent, text="Tryb Transkrypcji", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Radiobuttons dla trybów transkrypcji
        # 1. Transkrypcja lokalna - Whisper
        whisper_radio = ttk.Radiobutton(
            mode_frame, 
            text="💻 Transkrypcja Lokalna (Whisper)", 
            variable=self.transcription_mode, 
            value="local",
            command=lambda: self.root.after(100, self._update_transcription_mode)
        )
        
        if WHISPER_AVAILABLE:
            whisper_radio.config(state=tk.NORMAL)
        else:
            whisper_radio.config(state=tk.DISABLED)
                
        whisper_radio.pack(side=tk.LEFT, padx=(0, 10))
        
        # 2. Transkrypcja online - OpenAI Whisper API
        if OPENAI_AVAILABLE:
            openai_radio = ttk.Radiobutton(
                mode_frame, 
                text="☁️ Transkrypcja OpenAI Whisper", 
                variable=self.transcription_mode, 
                value="openai",
                command=lambda: self.root.after(100, self._update_transcription_mode)
            )
            
            if OPENAI_AVAILABLE:
                openai_radio.config(state=tk.NORMAL)
            else:
                openai_radio.config(state=tk.DISABLED)
                    
            openai_radio.pack(side=tk.LEFT, padx=(0, 10))

    def _create_model_section(self, parent: ttk.Frame) -> None:
        """
        Tworzy sekcję wyboru modelu.
        
        Args:
            parent: Widget rodzica
        """
        model_frame = ttk.LabelFrame(parent, text="Wybór Modelu", padding="10")
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Kontener dla modeli Whisper lokalnych
        self.whisper_models_container = ttk.Frame(model_frame)
        self.whisper_models_container.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.whisper_models_container, text="Model Whisper:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.whisper_model_combobox = ttk.Combobox(
            self.whisper_models_container,
            textvariable=self.selected_whisper_model,
            values=AVAILABLE_WHISPER_MODELS,
            state="readonly",
            width=20
        )
        self.whisper_model_combobox.pack(side=tk.LEFT, padx=(0, 10))
        
        # Ustawienie wybranego modelu Whisper w comboboxie
        if self.selected_whisper_model.get() in AVAILABLE_WHISPER_MODELS:
            selected_index = AVAILABLE_WHISPER_MODELS.index(self.selected_whisper_model.get())
            self.whisper_model_combobox.current(selected_index)
        elif AVAILABLE_WHISPER_MODELS:
            self.whisper_model_combobox.current(0)
            self.selected_whisper_model.set(AVAILABLE_WHISPER_MODELS[0])
        
        # Dodaj podświetlenie dla modelu Turbo, jeśli jest dostępny
        if "turbo" in AVAILABLE_WHISPER_MODELS and WHISPER_AVAILABLE:
            turbo_label = ttk.Label(
                self.whisper_models_container,
                text="✅ Model Turbo dostępny (8x szybszy)",
                foreground="#4caf50"  # Zielony kolor tekstu
            )
            turbo_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Informacja o instalacji Whisper (tylko jeśli nie jest zainstalowany)
        if not WHISPER_AVAILABLE:
            whisper_info = ttk.Label(
                self.whisper_models_container,
                text="🔴 Whisper nie zainstalowany",
                foreground="#f44336"  # Czerwony kolor tekstu
            )
            whisper_info.pack(side=tk.LEFT, padx=(10, 0))
        
        # Wspólne pole wyboru języka
        self.language_options_container = ttk.Frame(model_frame)
        self.language_options_container.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.language_options_container, text="Język:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Popularne języki dla Whisper
        language_options = [
            ("🌐 Automatycznie", ""),
            ("🇵🇱 Polski", "pl"),
            ("🇬🇧 Angielski", "en"),
            ("🇩🇪 Niemiecki", "de"),
            ("🇫🇷 Francuski", "fr"),
            ("🇪🇸 Hiszpański", "es"),
            ("🇮🇹 Włoski", "it"),
            ("🇷🇺 Rosyjski", "ru")
        ]
        
        language_display_values = [lang[0] for lang in language_options]
        self._language_codes = {lang[0]: lang[1] for lang in language_options}
        self._language_display = {code: name for name, code in self._language_codes.items()}
        self._language_display[""] = "🌐 Automatycznie"  # Zapewnij mapowanie pustego kodu na "Automatycznie"
        
        self.language_combobox = ttk.Combobox(
            self.language_options_container,
            values=language_display_values,
            state="readonly",
            width=20
        )
        self.language_combobox.pack(side=tk.LEFT)
        
        # Ustaw domyślny język
        lang_code = self.selected_language_code.get()
        lang_display = self._language_display.get(lang_code, "🌐 Automatycznie")
        
        # Znajdź indeks wybranego języka
        try:
            lang_index = language_display_values.index(lang_display)
            self.language_combobox.current(lang_index)
        except ValueError:
            # Jeśli nie znaleziono, ustaw domyślnie "Automatycznie"
            self.language_combobox.current(0)
        
        self.language_combobox.bind("<<ComboboxSelected>>", self._on_language_selected)

    def _create_action_section(self, parent: ttk.Frame) -> None:
        """
        Tworzy sekcję przycisków akcji.
        
        Args:
            parent: Widget rodzica
        """
        action_frame = ttk.LabelFrame(parent, text="Akcje", padding="10")
        action_frame.pack(fill=tk.X, pady=(0, 10))

        self.record_button = ttk.Button(
            action_frame, 
            text="🎙️ Rejestruj Mowę", 
            command=self.toggle_recording,
            style="Action.TButton"  # Używamy specjalnego stylu dla przycisku akcji
        )
        self.record_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.transcribe_button = ttk.Button(
            action_frame, 
            text="📝 Transkrybuj Nagranie", 
            command=self.transcribe_action, 
            state=tk.DISABLED
        )
        self.transcribe_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.status_label = ttk.Label(action_frame, text="Status: Gotowy")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)

    def _create_file_selection_section(self, parent: ttk.Frame) -> None:
        """
        Tworzy sekcję wyboru pliku audio.
        
        Args:
            parent: Widget rodzica
        """
        file_frame = ttk.LabelFrame(parent, text="Wybór Pliku Audio (opcjonalnie)", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.file_path_label = ttk.Label(file_frame, text="Brak wybranego pliku", foreground="gray")
        self.file_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        folder_button = ttk.Button(
            file_frame,
            text="📁 Pokaż folder",
            command=self.open_recordings_folder
        )
        folder_button.pack(side=tk.RIGHT, padx=(0, 5))

        browse_button = ttk.Button(
            file_frame,
            text="📂 Wybierz Plik Audio",
            command=self.browse_audio_file
        )
        browse_button.pack(side=tk.RIGHT)

    def browse_audio_file(self) -> None:
        """Otwiera dialog wyboru pliku audio."""
        filetypes = [
            ("Pliki Audio", "*.wav *.mp3 *.ogg *.flac"),
            ("Pliki WAV", "*.wav"),
            ("Pliki MP3", "*.mp3"),
            ("Wszystkie pliki", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="Wybierz plik audio",
            filetypes=filetypes,
            initialdir=RECORDINGS_DIR
        )
        
        if file_path:
            self.last_recorded_file = file_path
            self.file_path_var.set(file_path)
            self.file_path_label.config(
                text=f"Wybrany plik: {os.path.basename(file_path)}",
                foreground="white"  # Zmieniono kolor na biały dla ciemnego motywu
            )
            self.transcribe_button.config(state=tk.NORMAL)
            self._update_status(f"Wybrano plik: {os.path.basename(file_path)}")
            logger.info(f"Wybrano plik audio: {file_path}")

    def open_recordings_folder(self):
        """Otwiera folder z nagraniami w domyślnym eksploratorze plików."""
        try:
            if os.path.exists(RECORDINGS_DIR):
                os.startfile(RECORDINGS_DIR)  # Działa tylko na Windows
                self._update_status(f"Otwarto folder nagrań")
            else:
                self._show_message("warning", "Folder Nie Istnieje", 
                             f"Folder nagrań {RECORDINGS_DIR} nie istnieje.")
        except Exception as e:
            logger.error(f"Błąd podczas otwierania folderu nagrań: {e}")
            self._show_message("error", "Błąd", f"Nie można otworzyć folderu nagrań: {e}")

    def _create_transcription_section(self, parent: ttk.Frame) -> None:
        """
        Tworzy sekcję wyświetlania transkrypcji.
        
        Args:
            parent: Widget rodzica
        """
        result_frame = ttk.LabelFrame(parent, text="Transkrypcja", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        
        # Ustawienie propagacji wielkości ramki
        result_frame.pack_propagate(False)

        self.transcription_text = scrolledtext.ScrolledText(
            result_frame, 
            wrap=tk.WORD, 
            font=("Arial", 10),
            bg="#202020",  # Tło nieco jaśniejsze od głównego tła
            fg="#ffffff",  # Biały tekst
            insertbackground="#ffffff"  # Biały kursor
        )
        self.transcription_text.pack(fill=tk.BOTH, expand=True)
        self.transcription_text.config(state=tk.DISABLED)  # Domyślnie tylko do odczytu

    def _on_language_selected(self, event: Optional[tk.Event]) -> None:
        """
        Obsługuje wybór języka z comboboxa.
        
        Args:
            event: Obiekt zdarzenia (może być None)
        """
        selected_language_display = self.language_combobox.get()
        language_code = self._language_codes.get(selected_language_display, "")
        self.selected_language_code.set(language_code)
        
        # Zapisz wybrany język w konfiguracji
        self._save_settings({PREFERRED_LANGUAGE_CONFIG: language_code})
        
        logger.info(f"Wybrano język: {selected_language_display} (kod: {language_code or 'auto'})")

    def _on_whisper_model_selected(self, event: Optional[tk.Event]) -> None:
        """
        Obsługuje wybór modelu Whisper z comboboxa.
        """
        selected_model = self.selected_whisper_model.get()
        if selected_model in AVAILABLE_WHISPER_MODELS:
            # Zapisz wybrany model w konfiguracji
            self._save_settings({PREFERRED_MODEL_CONFIG: selected_model})
            logger.info(f"Wybrano model Whisper: {selected_model}")

    def _update_transcription_mode(self) -> None:
        """Aktualizuje widoczność sekcji w zależności od wybranego trybu transkrypcji."""
        mode = self.transcription_mode.get()
        
        # Najpierw ukryj wszystkie kontenery
        for container in [self.whisper_models_container, self.language_options_container]:
            container.pack_forget()
        
        # Sprawdź dostępność wybranej metody
        if mode == "local" and not WHISPER_AVAILABLE:
            messagebox.showwarning(
                "Whisper Niedostępny", 
                "Biblioteka Whisper nie jest zainstalowana lub nie działa z tą wersją Pythona."
            )
            mode = "openai"
            self.transcription_mode.set("openai")
        
        elif mode == "openai" and not OPENAI_AVAILABLE:
            messagebox.showwarning(
                "OpenAI Whisper API Niedostępne", 
                "Moduł OpenAI Whisper API nie jest dostępny."
            )
            mode = "local"
            self.transcription_mode.set("local")
        
        # Zapisz wybrany tryb w konfiguracji
        self._save_settings({PREFERRED_MODE_CONFIG: mode})
        
        # Teraz pokaż właściwe kontenery na podstawie trybu
        if mode == "local" and WHISPER_AVAILABLE:
            self.whisper_models_container.pack(fill=tk.X, pady=5)
            self.language_options_container.pack(fill=tk.X, pady=5)
            
            # Sprawdź czy model turbo jest wybrany
            if self.selected_whisper_model.get() == "turbo":
                self.transcribe_button.config(text="📝 Transkrybuj Lokalnie (Turbo)")
            else:
                self.transcribe_button.config(text="📝 Transkrybuj Lokalnie (Whisper)")
                
        elif mode == "openai" and OPENAI_AVAILABLE:
            self.language_options_container.pack(fill=tk.X, pady=5)
            self.transcribe_button.config(text="📝 Transkrybuj przez OpenAI")

    def _save_settings(self, settings: Dict[str, Any]) -> None:
        """
        Zapisuje ustawienia do konfiguracji.
        
        Args:
            settings: Słownik z ustawieniami do zaktualizowania
        """
        config = self.config.copy()
        config.update(settings)
        self.config = config
        try:
            save_config(config)
        except Exception as e:
            logger.error(f"Błąd zapisywania konfiguracji: {e}")

    def save_openai_key_action(self) -> None:
        """Zapisuje klucz API OpenAI i aktualizuje stan aplikacji."""
        key = self.openai_api_entry.get().strip()
        if not key:
            self._show_message("warning", "Pusty Klucz", "Klucz API OpenAI nie może być pusty.")
            return
        
        self._save_settings({OPENAI_KEY_CONFIG: key})
        self.openai_key_value = key
        if OPENAI_AVAILABLE and hasattr(self, 'openai_client'):
            self.openai_client.update_api_key(key)
        self._show_message("info", "Sukces", "Klucz API OpenAI został zapisany.")
        
        # Włącz tryb OpenAI, jeśli jest dostępny i klucz jest prawidłowy
        if OPENAI_AVAILABLE:
            self.transcription_mode.set("openai")
            self._update_transcription_mode()

    def toggle_recording(self) -> None:
        """Przełącza nagrywanie - uruchamia lub zatrzymuje."""
        if not self.is_recording_app_state:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self) -> None:
        """Rozpoczyna nagrywanie dźwięku."""
        if not self.recorder.start_recording():
            self._show_message(
                "error", 
                "Błąd Nagrywania", 
                "Nie można rozpocząć nagrywania. Sprawdź mikrofon i uprawnienia."
            )
            return
            
        self.is_recording_app_state = True
        self.record_button.config(text="⏹️ Zatrzymaj Nagrywanie")
        self._update_status("Nagrywanie...")
        self.transcribe_button.config(state=tk.DISABLED)
        
        # Wyczyść pole transkrypcji
        self.transcription_text.config(state=tk.NORMAL)
        self.transcription_text.delete(1.0, tk.END)
        self.transcription_text.config(state=tk.DISABLED)
        
        # Zresetuj wybrany plik
        self.last_recorded_file = None
        self.file_path_label.config(text="Brak wybranego pliku", foreground="gray")

    def _stop_recording(self) -> None:
        """Zatrzymuje nagrywanie i zapisuje plik."""
        self._update_status("Zapisywanie nagrania...")
        
        # Zatrzymanie nagrywania w głównym wątku - operacja I/O
        def stop_recording_thread():
            filepath = self.recorder.stop_recording()
            
            def finish_recording():
                self.is_recording_app_state = False
                self.record_button.config(text="🎙️ Rejestruj Mowę")
                
                if filepath:
                    self.last_recorded_file = filepath
                    self.file_path_label.config(
                        text=f"Nagranie: {os.path.basename(filepath)}",
                        foreground="white"  # Zmieniono kolor na biały dla ciemnego motywu
                    )
                    self._update_status(f"Nagranie zapisane ({os.path.basename(filepath)})")
                    self.transcribe_button.config(state=tk.NORMAL)
                    # Usunięto komunikat - tylko log
                    logger.info(f"Nagranie zostało zapisane jako: {filepath}")
                else:
                    self._update_status("Błąd zapisu nagrania.")
                    self.file_path_label.config(text="Błąd zapisu nagrania", foreground="red")
                    # Komunikat błędu zostawiamy, bo jest krytyczny
                    self._show_message("error", "Błąd Zapisu", "Nie udało się zapisać nagrania.")
                    self.transcribe_button.config(state=tk.DISABLED)
            
            self._update_gui(finish_recording)
        
        self._run_in_thread(stop_recording_thread)

    def transcribe_action(self) -> None:
        """Rozpoczyna proces transkrypcji nagrania."""
        if not self.last_recorded_file:
            self._show_message("warning", "Brak Nagrania", "Najpierw nagraj lub wskaż plik audio.")
            return
        
        mode = self.transcription_mode.get()
        
        if mode == "local":
            if WHISPER_AVAILABLE:
                self._transcribe_local()
            else:
                self._show_message("warning", "Whisper Niedostępny", 
                                  "Biblioteka Whisper nie jest zainstalowana. Przełączanie na transkrypcję online...")
                self.transcription_mode.set("openai")
                self._update_transcription_mode()
                self._transcribe_with_openai()
        else:  # mode == "openai"
            if OPENAI_AVAILABLE:
                self._transcribe_with_openai()
            else:
                self._show_message("warning", "OpenAI API Niedostępne", 
                                 "Moduł OpenAI API nie jest dostępny. Przełączanie na transkrypcję lokalną...")
                self.transcription_mode.set("local")
                self._update_transcription_mode()
                self._transcribe_local()

    def _transcribe_local(self) -> None:
        """Wykonuje lokalną transkrypcję przy użyciu Whisper."""
        if not WHISPER_AVAILABLE:
            self._show_message("error", "Whisper Niedostępny", 
                              "Biblioteka OpenAI Whisper nie jest zainstalowana lub nie działa z tą wersją Pythona.")
            return
            
        selected_model = self.selected_whisper_model.get()
        language_code = self.selected_language_code.get()
        
        if not selected_model:
            self._show_message("warning", "Brak Modelu", "Wybierz model Whisper z listy.")
            return
        
        model_display = selected_model
        if selected_model == "turbo":
            model_display = "Turbo (8x szybszy)"
            
        self._update_status(f"Transkrypcja lokalna (model: {model_display}, język: {language_code or 'auto'})...")
        self.transcribe_button.config(state=tk.DISABLED)
        self.record_button.config(state=tk.DISABLED)
        
        # Uruchom transkrypcję w osobnym wątku
        self._run_in_thread(
            partial(self._transcribe_local_thread, self.last_recorded_file, selected_model, language_code)
        )

    def _transcribe_with_openai(self) -> None:
        """Wykonuje transkrypcję przy użyciu OpenAI Whisper API."""
        if not OPENAI_AVAILABLE:
            self._show_message("error", "OpenAI API Niedostępne", 
                             "Moduł OpenAI API nie jest dostępny.")
            return
            
        if not self.openai_key_value:
            self._show_message("warning", "Brak Klucza API", 
                             "Wprowadź i zapisz klucz API OpenAI w sekcji konfiguracji OpenAI.")
            return
            
        language_code = self.selected_language_code.get()
        
        self._update_status(f"Transkrypcja OpenAI Whisper (język: {language_code or 'auto'})...")
        self.transcribe_button.config(state=tk.DISABLED)
        self.record_button.config(state=tk.DISABLED)
        
        # Uruchom transkrypcję w osobnym wątku
        self._run_in_thread(
            partial(self._transcribe_openai_thread, self.last_recorded_file, language_code)
        )

    def _transcribe_local_thread(self, audio_path: str, model_name: str, language_code: str) -> None:
        """
        Wątek wykonujący lokalną transkrypcję audio.
        
        Args:
            audio_path: Ścieżka do pliku audio
            model_name: Nazwa modelu Whisper
            language_code: Kod języka (może być pusty)
        """
        logger.info(f"Rozpoczynanie lokalnej transkrypcji pliku: {audio_path} z modelem Whisper: {model_name}, język: {language_code or 'auto'}")
        
        try:
            # Sprawdź czy plik istnieje
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Plik audio nie istnieje: {audio_path}")
                
            # Sprawdź rozmiar pliku do debugowania
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            logger.info(f"Rozmiar pliku: {file_size_mb:.2f} MB")
            
            # Lokalnie zaimportuj funkcję transkrypcji, aby obsłużyć potencjalny brak modułu
            if LOCAL_STT_MODULE_AVAILABLE:
                from modules.local_stt import transcribe_audio_local
                transcript, error_msg = transcribe_audio_local(
                    audio_path, 
                    model_name=model_name, 
                    language=language_code if language_code else None
                )
            else:
                # Bezpośrednie użycie Whisper, jeśli moduł local_stt jest niedostępny
                try:
                    import whisper
                    model = whisper.load_model(model_name)
                    
                    options = {"fp16": False}
                    if language_code:
                        options["language"] = language_code
                        
                    result = model.transcribe(audio_path, **options)
                    transcript = result["text"].strip()
                    error_msg = None
                    
                    detected_lang = result.get("language", "nie wykryto")
                    logger.info(f"Lokalna transkrypcja zakończona. Wykryty język: {detected_lang}.")
                    
                except Exception as e:
                    transcript = None
                    error_msg = f"Błąd podczas bezpośredniej transkrypcji Whisper: {str(e)}"
                    logger.error(error_msg)
            
            def update_transcription_ui():
                if error_msg:
                    self._handle_transcription_error(error_msg)
                elif transcript is not None:
                    self._handle_successful_transcription(transcript)
                else:
                    self._handle_transcription_error("Wystąpił nieznany błąd podczas transkrypcji.")
                
                # Zawsze odblokuj przyciski
                self.transcribe_button.config(state=tk.NORMAL if self.last_recorded_file else tk.DISABLED)
                self.record_button.config(state=tk.NORMAL)
            
            self._update_gui(update_transcription_ui)
            
        except ImportError:
            logger.error("Moduł 'whisper' nie został znaleziony.")
            self._update_gui(lambda: self._handle_transcription_error(
                "Brak biblioteki Whisper. Zainstaluj ją używając: pip install openai-whisper"
            ))
            # Odblokuj przyciski
            self._update_gui(lambda: self.transcribe_button.config(state=tk.NORMAL if self.last_recorded_file else tk.DISABLED))
            self._update_gui(lambda: self.record_button.config(state=tk.NORMAL))
        except Exception as e:
            logger.error(f"Wyjątek podczas lokalnej transkrypcji: {str(e)}")
            self._update_gui(
                lambda: self._handle_transcription_error(f"Błąd podczas lokalnej transkrypcji: {str(e)}")
            )

    def _transcribe_openai_thread(self, audio_path: str, language_code: str) -> None:
        """
        Wątek wykonujący transkrypcję audio przez OpenAI Whisper API.
        
        Args:
            audio_path: Ścieżka do pliku audio
            language_code: Kod języka (może być pusty)
        """
        logger.info(f"Rozpoczynanie transkrypcji OpenAI pliku: {audio_path}, język: {language_code or 'auto'}")
        
        try:
            # Sprawdź czy plik istnieje
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Plik audio nie istnieje: {audio_path}")
                
            # Sprawdź rozmiar pliku do debugowania
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            logger.info(f"Rozmiar pliku: {file_size_mb:.2f} MB")
            
            # Wykonaj transkrypcję
            transcript, error_msg = self.openai_client.transcribe_audio(
                audio_path, 
                language=language_code if language_code else None
            )
            
            def update_transcription_ui():
                if error_msg:
                    self._handle_transcription_error(error_msg)
                elif transcript is not None:
                    self._handle_successful_transcription(transcript)
                else:
                    self._handle_transcription_error("Wystąpił nieznany błąd podczas transkrypcji.")
                
                # Zawsze odblokuj przyciski
                self.transcribe_button.config(state=tk.NORMAL if self.last_recorded_file else tk.DISABLED)
                self.record_button.config(state=tk.NORMAL)
            
            self._update_gui(update_transcription_ui)
            
        except Exception as e:
            logger.error(f"Wyjątek podczas transkrypcji OpenAI: {str(e)}")
            self._update_gui(
                lambda: self._handle_transcription_error(f"Błąd podczas transkrypcji OpenAI: {str(e)}")
            )

    def _handle_successful_transcription(self, transcript: str) -> None:
        """
        Obsługuje udaną transkrypcję.
        
        Args:
            transcript: Tekst transkrypcji
        """
        self._update_status("Transkrypcja zakończona.")
        self.transcription_text.config(state=tk.NORMAL)
        self.transcription_text.delete(1.0, tk.END)
        self.transcription_text.insert(tk.END, transcript)
        self.transcription_text.config(state=tk.DISABLED)
        
        # Kopiuj transkrypcję do schowka
        self.root.clipboard_clear()
        self.root.clipboard_append(transcript)
        self._update_status("Transkrypcja zakończona i skopiowana do schowka ✓")
        
        # Usunięto komunikat - tylko log
        logger.info("Transkrypcja zakończona pomyślnie i skopiowana do schowka.")

    def _handle_transcription_error(self, error_msg: str) -> None:
        """
        Obsługuje błąd transkrypcji.
        
        Args:
            error_msg: Komunikat błędu
        """
        self._update_status("❌ Błąd transkrypcji")
        self._show_message("error", "Błąd Transkrypcji", error_msg)
        self.transcription_text.config(state=tk.NORMAL)
        self.transcription_text.delete(1.0, tk.END)  # Wyczyść przed dodaniem błędu
        self.transcription_text.insert(tk.END, f"--- BŁĄD ---\n{error_msg}\n")
        self.transcription_text.config(state=tk.DISABLED)

    def _update_status(self, message: str) -> None:
        """
        Aktualizuje tekst etykiety statusu.
        
        Args:
            message: Nowa wiadomość statusu
        """
        self.status_label.config(text=f"Status: {message}")
        self.root.update_idletasks()

    def _show_message(self, msg_type: str, title: str, message: str) -> None:
        """
        Wyświetla okno dialogowe z komunikatem.
        
        Args:
            msg_type: Typ komunikatu ('info', 'warning', 'error')
            title: Tytuł okna
            message: Treść komunikatu
        """
        if msg_type == "info":
            messagebox.showinfo(title, message)
        elif msg_type == "warning":
            messagebox.showwarning(title, message)
        elif msg_type == "error":
            messagebox.showerror(title, message)

    def _run_in_thread(self, func: Callable, daemon: bool = True) -> None:
        """
        Uruchamia funkcję w osobnym wątku.
        
        Args:
            func: Funkcja do uruchomienia
            daemon: Czy wątek ma być demonem (kończy się wraz z głównym wątkiem)
        """
        thread = threading.Thread(target=func, daemon=daemon)
        thread.start()

    def _update_gui(self, func: Callable) -> None:
        """
        Bezpiecznie aktualizuje GUI z głównego wątku.
        
        Args:
            func: Funkcja aktualizująca GUI
        """
        self.root.after(0, func)


if __name__ == "__main__":
    # Sprawdź czy moduł Whisper jest dostępny i jakie modele są zainstalowane
    if WHISPER_AVAILABLE:
        try:
            import whisper
            available_models = whisper.available_models()
            logger.info(f"Dostępne modele Whisper: {', '.join(available_models)}")
            
            # Sprawdź czy model "turbo" jest dostępny
            if "turbo" in available_models:
                logger.info("Model 'turbo' jest dostępny!")
            
        except Exception as e:
            logger.warning(f"Nie można sprawdzić dostępnych modeli Whisper: {e}")
    
    root = tk.Tk()
    app = DictAItorApp(root)
    root.mainloop()