# Piper Studio – Piper Text-to-Speech Front-End

`Piper Studio` is a small Tkinter application that ships with Phantom to make it
easier to experiment with high quality [Piper](https://github.com/rhasspy/piper)
voices. The interface embraces a dark, Windows 11–inspired aesthetic and keeps
the workflow focused on the essentials: choose a curated voice, load or edit a
script, then play the audio or export it to an MP3 file.

## Features

- Curated voice list containing three of the community favourites:
  - `en_US-lessac-high` – warm, articulate US English voice.
  - `en_US-libritts-high` – expressive US English LibriTTS voice.
  - `en_GB-semaine-high` – calm, polished British English voice.
- Load text from `.txt` files or type directly into the editor.
- One-click playback (using `simpleaudio`, Windows `winsound`, or `ffplay`).
- MP3 export via `pydub` or the `ffmpeg` command line tool.
- Real-time status updates so you know when synthesis or conversion finishes.

## Requirements

1. [Piper](https://github.com/rhasspy/piper) must be installed and available on
   your system `PATH`, or you can browse for the executable inside the app.
2. Download the voice models listed in `data/piper_voices.json` and place them
   under the repository `voices/` directory, preserving the folder structure.
3. For playback and MP3 export you need one of the following optional tools:
   - Playback: [`simpleaudio`](https://github.com/hamiltron/py-simple-audio),
     Windows `winsound`, or `ffplay` (part of FFmpeg).
   - MP3 export: [`pydub`](https://github.com/jiaaro/pydub) **or** the `ffmpeg`
     command line tool.

## Running the app

From the root of the repository run:

```bash
python -m scripts.piper_tts_gui
```

The application remembers neither settings nor text between sessions, so the
behaviour is predictable and side-effect free. When a voice is missing the UI
shows download links so you can fetch the ONNX model and JSON config quickly.

## Customising voices

The curated voice list lives in `data/piper_voices.json`. Each entry contains the
model and config file paths (relative to the repository root), a sample rate and
optional download URLs. Feel free to add more entries for personal use; the GUI
will automatically list them the next time it starts.

## Troubleshooting

- **Playback errors** – Install `simpleaudio` (`pip install simpleaudio`) or
  make sure `ffplay` is on your `PATH`.
- **MP3 export errors** – Install `pydub` plus FFmpeg, or provide the FFmpeg
  executable directly.
- **Voice marked as missing** – Verify the model and config files exist at the
  paths defined in the JSON registry.

Happy synthesising!
