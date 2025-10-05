"""Dark-themed Piper text-to-speech GUI inspired by Windows 11."""

from __future__ import annotations

import queue
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import piper_tts


APP_TITLE = "Piper Studio"
WINDOW_MIN_WIDTH = 820
WINDOW_MIN_HEIGHT = 600


class PiperApp(tk.Tk):
    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.registry = piper_tts.load_registry_from_default(base_dir / "data")
        self.tts = piper_tts.PiperTTS(voices=self.registry)
        self._status_queue: "queue.Queue[str]" = queue.Queue()

        self.title(APP_TITLE)
        self.geometry(f"{WINDOW_MIN_WIDTH}x{WINDOW_MIN_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self._setup_theme()
        self._create_widgets()
        self.after(150, self._poll_status_queue)

    # ------------------------------------------------------------------ UI setup

    def _setup_theme(self) -> None:
        self.configure(bg="#101014")
        style = ttk.Style()
        style.theme_use("clam")

        dark_bg = "#101014"
        panel_bg = "#1b1f29"
        accent = "#4f8cff"
        text_color = "#f4f5f7"
        muted_text = "#9aa0ac"

        style.configure("TFrame", background=dark_bg)
        style.configure("Card.TFrame", background=panel_bg, relief="flat")
        style.configure("Accent.TButton", background=accent, foreground=text_color, borderwidth=0, focusthickness=3)
        style.map(
            "Accent.TButton",
            background=[("active", "#6a9dff"), ("disabled", "#243150")],
            foreground=[("disabled", muted_text)],
        )
        style.configure("Secondary.TButton", background="#252a36", foreground=text_color, borderwidth=0)
        style.map(
            "Secondary.TButton",
            background=[("active", "#313747")],
            foreground=[("disabled", muted_text)],
        )
        style.configure("TLabel", background=dark_bg, foreground=text_color)
        style.configure("Muted.TLabel", background=dark_bg, foreground=muted_text)
        style.configure("Card.TLabel", background=panel_bg, foreground=text_color)
        style.configure("TMenubutton", background=panel_bg, foreground=text_color)
        style.configure("TCombobox", fieldbackground=panel_bg, foreground=text_color, background=panel_bg)
        style.map("TCombobox", fieldbackground=[("readonly", panel_bg)], selectbackground=[("readonly", panel_bg)])
        style.configure("Status.TLabel", background=panel_bg, foreground=muted_text)

    def _create_widgets(self) -> None:
        root_frame = ttk.Frame(self)
        root_frame.pack(fill="both", expand=True, padx=24, pady=24)

        header = ttk.Label(root_frame, text="Piper Studio", font=("Segoe UI Variable Display", 20, "bold"))
        header.pack(anchor="w")
        subtitle = ttk.Label(
            root_frame,
            text="Generate natural speech with curated Piper voices.",
            style="Muted.TLabel",
            font=("Segoe UI", 11),
        )
        subtitle.pack(anchor="w", pady=(2, 16))

        controls = ttk.Frame(root_frame, style="Card.TFrame")
        controls.pack(fill="x", pady=(0, 16))

        # Piper executable selector
        exe_label = ttk.Label(controls, text="Piper executable", style="Card.TLabel")
        exe_label.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 4))
        self.exe_var = tk.StringVar(value=self.tts.piper_executable)
        self.exe_var.trace_add("write", lambda *_: self.tts.update_executable(self.exe_var.get()))
        exe_entry = ttk.Entry(controls, textvariable=self.exe_var, width=50)
        exe_entry.grid(row=1, column=0, padx=18, pady=(0, 12), sticky="we")
        browse_btn = ttk.Button(
            controls,
            text="Browse",
            style="Secondary.TButton",
            command=self._browse_executable,
        )
        browse_btn.grid(row=1, column=1, padx=(0, 18), pady=(0, 12))

        # Voice selector
        voice_label = ttk.Label(controls, text="Voice", style="Card.TLabel")
        voice_label.grid(row=2, column=0, sticky="w", padx=18, pady=(4, 4))
        self.voice_var = tk.StringVar(value=self._default_voice())
        self.voice_combo = ttk.Combobox(
            controls,
            textvariable=self.voice_var,
            state="readonly",
            values=[voice.id for voice in self.registry],
        )
        self.voice_combo.grid(row=3, column=0, padx=18, pady=(0, 12), sticky="we")
        self.voice_combo.bind("<<ComboboxSelected>>", lambda *_: self._update_voice_details())

        self.voice_details = ttk.Label(controls, text="", style="Status.TLabel", justify="left", wraplength=520)
        self.voice_details.grid(row=4, column=0, columnspan=2, padx=18, pady=(0, 18), sticky="we")

        controls.columnconfigure(0, weight=1)

        # Text area card
        text_card = ttk.Frame(root_frame, style="Card.TFrame")
        text_card.pack(fill="both", expand=True, pady=(0, 16))

        text_header = ttk.Label(text_card, text="Script", style="Card.TLabel", font=("Segoe UI", 11, "bold"))
        text_header.pack(anchor="w", padx=18, pady=(18, 6))

        text_toolbar = ttk.Frame(text_card, style="Card.TFrame")
        text_toolbar.pack(fill="x", padx=18)
        load_btn = ttk.Button(text_toolbar, text="Load text file", style="Secondary.TButton", command=self._load_text_file)
        load_btn.pack(side="left")
        clear_btn = ttk.Button(text_toolbar, text="Clear", style="Secondary.TButton", command=lambda: self.text_widget.delete("1.0", "end"))
        clear_btn.pack(side="left", padx=(8, 0))

        text_container = ttk.Frame(text_card, style="Card.TFrame")
        text_container.pack(fill="both", expand=True, padx=18, pady=(6, 18))
        self.text_widget = tk.Text(
            text_container,
            wrap="word",
            height=12,
            bg="#151922",
            fg="#f4f5f7",
            insertbackground="#f4f5f7",
            font=("Segoe UI", 11),
            relief="flat",
            highlightthickness=1,
            highlightbackground="#2a3140",
        )
        self.text_widget.pack(fill="both", expand=True)

        # Action buttons
        action_bar = ttk.Frame(root_frame, style="Card.TFrame")
        action_bar.pack(fill="x")

        self.play_btn = ttk.Button(action_bar, text="Play", style="Accent.TButton", command=self._play_audio)
        self.play_btn.pack(side="left", padx=18, pady=18)

        self.save_btn = ttk.Button(action_bar, text="Save as MP3", style="Accent.TButton", command=self._export_mp3)
        self.save_btn.pack(side="left")

        self.status_label = ttk.Label(action_bar, text="Ready.", style="Status.TLabel")
        self.status_label.pack(side="right", padx=18)

        self._update_voice_details()

    # ------------------------------------------------------------------ UI helpers

    def _default_voice(self) -> str:
        voices = list(self.registry)
        return voices[0].id if voices else ""

    def _update_voice_details(self) -> None:
        try:
            voice = self.registry.get(self.voice_var.get())
        except KeyError:
            self.voice_details.config(text="")
            return

        exists = voice.exists(self.base_dir)
        status = "Available" if exists else "Missing files"
        hint = "" if exists else f"\nDownload: {voice.download}\nConfig: {voice.download_config}"
        description = (
            f"{voice.name}\n"
            f"Language: {voice.language} • Quality: {voice.quality}\n"
            f"Status: {status}{hint}"
        )
        self.voice_details.config(text=description)

    def _browse_executable(self) -> None:
        filename = filedialog.askopenfilename(title="Select Piper executable")
        if filename:
            self.exe_var.set(filename)
            self.tts.update_executable(filename)
            self._set_status("Updated Piper executable path.")

    def _load_text_file(self) -> None:
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf8") as handle:
                content = handle.read()
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Failed to read file:\n{exc}")
            return
        self.text_widget.delete("1.0", "end")
        self.text_widget.insert("1.0", content)
        self._set_status(f"Loaded text from {filename}.")

    # ------------------------------------------------------------------ Actions

    def _play_audio(self) -> None:
        self._launch_worker(self._play_worker)

    def _export_mp3(self) -> None:
        filename = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3", "*.mp3")])
        if not filename:
            return
        self._launch_worker(lambda: self._export_worker(Path(filename)))

    # ------------------------------------------------------------------ Workers

    def _launch_worker(self, task):
        thread = threading.Thread(target=self._safe_execute, args=(task,), daemon=True)
        thread.start()

    def _safe_execute(self, task):
        self._set_status("Processing…")
        self._toggle_buttons(False)
        try:
            task()
            self._set_status("Completed.")
        except piper_tts.PiperError as exc:
            self._set_status("Error")
            messagebox.showerror(APP_TITLE, str(exc))
        except Exception as exc:  # pragma: no cover - defensive programming
            self._set_status("Error")
            messagebox.showerror(APP_TITLE, f"Unexpected error: {exc}")
        finally:
            self._toggle_buttons(True)

    def _play_worker(self):
        voice = self.registry.get(self.voice_var.get())
        text = self.text_widget.get("1.0", "end")
        with tempfile.TemporaryDirectory(prefix="piper-studio-") as tmpdir:
            wav_path = Path(tmpdir) / "preview.wav"
            self.tts.synthesise_to_wav(text, voice, self.base_dir, wav_path)
            self.tts.play_audio(wav_path)

    def _export_worker(self, mp3_path: Path):
        voice = self.registry.get(self.voice_var.get())
        text = self.text_widget.get("1.0", "end")
        with tempfile.TemporaryDirectory(prefix="piper-studio-") as tmpdir:
            wav_path = Path(tmpdir) / "export.wav"
            self.tts.synthesise_to_wav(text, voice, self.base_dir, wav_path)
            self.tts.convert_wav_to_mp3(wav_path, mp3_path)

    # ------------------------------------------------------------------ Utilities

    def _toggle_buttons(self, state: bool) -> None:
        new_state = "!disabled" if state else "disabled"
        for widget in (self.play_btn, self.save_btn):
            widget.state([new_state])

    def _set_status(self, message: str) -> None:
        self._status_queue.put(message)

    def _poll_status_queue(self) -> None:
        try:
            while True:
                message = self._status_queue.get_nowait()
                self.status_label.config(text=message)
        except queue.Empty:
            pass
        finally:
            self.after(150, self._poll_status_queue)


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    app = PiperApp(base_dir)
    app.mainloop()


if __name__ == "__main__":
    main()
