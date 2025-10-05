"""Helper utilities for interacting with Piper text-to-speech voices.

The :class:`PiperTTS` helper is intentionally lightweight and works with the
`piper` command line interface. It provides convenience wrappers that the GUI
can use for synthesis, playback and exporting audio.

The helper favours standard library dependencies so that it can be deployed in
the same environments where Phantom is typically compiled. Optional extras such
as ``pydub`` or ``simpleaudio`` will be used if they are available at runtime
but are not required.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional


@dataclass
class PiperVoice:
    """Metadata describing a Piper voice model."""

    id: str
    name: str
    description: str
    language: str
    quality: str
    model: str
    config: str
    sample_rate: int
    download: Optional[str] = None
    download_config: Optional[str] = None
    speaker: Optional[str] = None

    def model_path(self, base_dir: Path) -> Path:
        return (base_dir / self.model).expanduser().resolve()

    def config_path(self, base_dir: Path) -> Path:
        return (base_dir / self.config).expanduser().resolve()

    def exists(self, base_dir: Path) -> bool:
        return self.model_path(base_dir).is_file() and self.config_path(base_dir).is_file()


class PiperVoiceRegistry:
    """Registry holding the voices that are available to the application."""

    def __init__(self, voices: Iterable[PiperVoice]):
        self._voices: Dict[str, PiperVoice] = {voice.id: voice for voice in voices}

    def __iter__(self):
        return iter(self._voices.values())

    def __len__(self) -> int:
        return len(self._voices)

    def get(self, voice_id: str) -> PiperVoice:
        if voice_id not in self._voices:
            raise KeyError(f"Unknown Piper voice '{voice_id}'.")
        return self._voices[voice_id]

    @classmethod
    def from_json(cls, path: Path) -> "PiperVoiceRegistry":
        with open(path, "r", encoding="utf8") as handle:
            raw = json.load(handle)
        voices = [PiperVoice(**entry) for entry in raw]
        return cls(voices)


class PiperError(RuntimeError):
    """Raised when synthesis fails."""


class PiperTTS:
    """Thin wrapper around the ``piper`` executable."""

    def __init__(self, piper_executable: Optional[str] = None, voices: Optional[PiperVoiceRegistry] = None):
        self.piper_executable = piper_executable or shutil.which("piper") or "piper"
        self.voices = voices

    def update_executable(self, executable: str) -> None:
        self.piper_executable = executable

    def ensure_executable(self) -> str:
        candidate = shutil.which(self.piper_executable) if os.path.sep not in self.piper_executable else self.piper_executable
        if candidate and Path(candidate).is_file():
            return candidate
        raise PiperError(
            "Unable to locate the 'piper' executable. Please install Piper or "
            "specify the full path to the executable in the application settings."
        )

    def synthesise_to_wav(
        self,
        text: str,
        voice: PiperVoice,
        base_dir: Path,
        output_path: Path,
        length_scale: Optional[float] = None,
        speaker: Optional[int] = None,
    ) -> Path:
        if not text.strip():
            raise PiperError("No text supplied for synthesis.")

        if not voice.exists(base_dir):
            raise PiperError(
                f"Voice '{voice.name}' is not ready. Expected to find model at "
                f"{voice.model_path(base_dir)} and config at {voice.config_path(base_dir)}."
            )

        executable = self.ensure_executable()

        cmd = [
            executable,
            "--model",
            str(voice.model_path(base_dir)),
            "--config",
            str(voice.config_path(base_dir)),
            "--output_file",
            str(output_path),
        ]

        if length_scale is not None:
            cmd.extend(["--length_scale", str(length_scale)])

        if speaker is not None:
            cmd.extend(["--speaker", str(speaker)])
        elif voice.speaker is not None:
            cmd.extend(["--speaker", str(voice.speaker)])

        process = subprocess.run(
            cmd,
            input=text.encode("utf8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if process.returncode != 0:
            raise PiperError(
                "Piper synthesis failed:\n" + process.stderr.decode("utf8", errors="ignore")
            )

        if not output_path.is_file():
            raise PiperError("Piper synthesis finished but the output file was not created.")

        return output_path

    # Audio helpers -----------------------------------------------------------------

    def play_audio(self, wav_path: Path) -> None:
        """Attempt to play a WAV file using available backends."""

        wav_path = wav_path.resolve()
        if not wav_path.is_file():
            raise PiperError(f"Audio file {wav_path} does not exist.")

        # Prefer simpleaudio when available because it is lightweight and synchronous.
        try:
            import simpleaudio  # type: ignore

            wave_obj = simpleaudio.WaveObject.from_wave_file(str(wav_path))
            play_obj = wave_obj.play()
            play_obj.wait_done()
            return
        except ImportError:
            pass

        # Fallback to winsound on Windows.
        if sys.platform.startswith("win"):
            try:
                import winsound

                winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
                return
            except Exception as exc:  # pragma: no cover - platform specific
                raise PiperError(f"Unable to play audio using winsound: {exc}")

        # Try ffplay if present in PATH.
        ffplay = shutil.which("ffplay")
        if ffplay:
            process = subprocess.run([ffplay, "-nodisp", "-autoexit", str(wav_path)])
            if process.returncode == 0:
                return

        raise PiperError(
            "Audio playback requires either the 'simpleaudio' Python package, Windows winsound support, "
            "or the 'ffplay' command. Please install one of these to use playback."
        )

    def convert_wav_to_mp3(self, wav_path: Path, mp3_path: Path) -> None:
        wav_path = wav_path.resolve()
        mp3_path = mp3_path.resolve()

        if not wav_path.is_file():
            raise PiperError(f"Expected WAV file at {wav_path}")

        # Try pydub first as it gives the best experience.
        try:
            from pydub import AudioSegment  # type: ignore

            audio = AudioSegment.from_wav(str(wav_path))
            audio.export(str(mp3_path), format="mp3")
            return
        except ImportError:
            pass

        # Fallback to ffmpeg/ffprobe.
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            process = subprocess.run(
                [ffmpeg, "-y", "-i", str(wav_path), str(mp3_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if process.returncode == 0:
                return
            raise PiperError(
                "ffmpeg failed to convert audio:\n" + process.stderr.decode("utf8", errors="ignore")
            )

        raise PiperError(
            "MP3 export requires either the 'pydub' Python package (with ffmpeg installed) or the 'ffmpeg' command."
        )


def load_registry_from_default(data_path: Path) -> PiperVoiceRegistry:
    """Load the bundled voice registry."""

    return PiperVoiceRegistry.from_json(data_path / "piper_voices.json")


__all__ = [
    "PiperError",
    "PiperTTS",
    "PiperVoice",
    "PiperVoiceRegistry",
    "load_registry_from_default",
]
