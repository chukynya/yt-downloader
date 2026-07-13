# YouTube MP3 & MP4 Downloader

A simple, cross-platform command-line tool to download a YouTube video as **MP4**
or extract its audio as **MP3**. Paste any link — including playlist or radio
URLs — and it automatically trims it down to the **single video** you asked for,
then lets you pick the quality.

## Features

- 🎬 **Video (MP4)** up to **8K (4320p)** — plus 4K, 1440p, 1080p, 720p and lower
- 🎵 **Audio (MP3)** from 96 kbps up to **320 kbps** (the MP3 maximum)
- ✂️ **Auto-trims playlist/radio links** — `…watch?v=ID&list=RD…&start_radio=1`
  downloads only video `ID`, never the whole mix
- ⭐ A **recommended** default for each menu — just press Enter to accept it
- 💻 Works on **Linux, Windows and macOS**

## Requirements

- **Python 3.10 or higher** (uses modern type-hint syntax)
- **yt-dlp** (installed via `requirements.txt`, below)
- **FFmpeg** — *recommended*; required for MP3 conversion and for merging video
  above 720p. It is a **system program**, installed separately from pip.
- **Deno or Node.js** — *optional*; makes YouTube extraction more reliable.

---

## Installation

### 1. Get the code

```bash
git clone https://github.com/YOUR_USERNAME/yt-downloader.git
cd yt-downloader
```

### 2. Create and activate a virtual environment (`.env`)

This keeps the Python dependencies isolated to the project instead of installing
them system-wide.

**Linux / macOS**
```bash
python3 -m venv .env
source .env/bin/activate
```

**Windows — PowerShell**
```powershell
python -m venv .env
.\.env\Scripts\Activate.ps1
```
> If PowerShell blocks the activation script, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**Windows — Command Prompt (cmd)**
```bat
python -m venv .env
.\.env\Scripts\activate.bat
```

Your shell prompt should now be prefixed with `(.env)`. To leave the environment
later, just run `deactivate`.

### 3. Install the Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg (recommended — separate system install)

FFmpeg is **not** a pip package; install it with your OS package manager.

**Linux — Fedora**
```bash
# FFmpeg on Fedora needs the RPM Fusion repository first:
sudo dnf install \
  https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
sudo dnf install ffmpeg
```
> Without RPM Fusion, `dnf` only offers the limited `ffmpeg-free` package.

**Linux — Debian / Ubuntu**
```bash
sudo apt update && sudo apt install ffmpeg
```

**Windows**
```powershell
winget install Gyan.FFmpeg
# or, with Chocolatey:
choco install ffmpeg
```

**macOS**
```bash
brew install ffmpeg
```

Verify it is on your PATH: `ffmpeg -version`.

### 5. Install a JavaScript runtime (optional)

Improves the reliability of YouTube's format extraction.

**Windows**
```powershell
winget install DenoLand.Deno
```

**Linux / macOS**
```bash
curl -fsSL https://deno.land/install.sh | sh
```

---

## Usage

With the `.env` environment activated:

```bash
python main.py
```

Then follow the prompts:

1. **Enter a YouTube URL.** Playlist/radio parameters are stripped automatically;
   you'll see a `→ Cleaned to single video:` line when that happens.
2. **Choose Video (MP4) or Audio (MP3).**
3. **Pick a quality** — or just press **Enter** to take the recommended option.

Downloaded files are saved in the `downloads/` folder.

### Quality reference

| Video (MP4)        | Audio (MP3)         |
| ------------------ | ------------------- |
| Best available     | 320 kbps *(max)* ⭐ |
| 8K — 4320p         | 256 kbps            |
| 4K — 2160p         | 192 kbps            |
| 1440p (2K)         | 160 kbps            |
| 1080p ⭐ *(rec.)*  | 128 kbps            |
| 720p / 480p / 360p | 96 kbps             |
| Lowest             |                     |

> **Why does MP3 stop at 320 kbps?** That is the maximum bitrate the MP3 format
> itself supports — there is no valid MP3 above it. **8K (4320p)** is likewise the
> highest resolution YouTube publishes, so there is nothing above 4K to offer.

---

## Notes & troubleshooting

- **Video above 720p / MP3 conversion needs FFmpeg.** Without it, high-resolution
  video can't be merged and audio is saved as **M4A** instead of MP3.
- **Not every video offers every resolution.** If a video has no 8K/4K stream, the
  next best available quality is downloaded automatically.
- **Extraction errors / "unavailable" formats?** Update yt-dlp — YouTube changes
  frequently: `pip install -U yt-dlp`.
- Supported link forms: `youtube.com/watch`, `youtu.be/…`, `/shorts/…`,
  `/live/…`, `/embed/…`.

---

## For developers

**Project layout**

| File | What it holds |
| --- | --- |
| `ytdl_core.py` | Pure logic — URL cleaning, quality tables, format codes, environment checks. No yt-dlp, no console I/O, so it's easy to test. |
| `main.py` | The interactive app — yt-dlp options, downloading, and the menu loop. |
| `tests/test_core.py` | Unit tests for `ytdl_core` (no network, no yt-dlp needed). |

**Running the tests**

```bash
python -m unittest discover -s tests -t .
# or simply:
python tests/test_core.py
```

The quality menus are data-driven: edit a row in `VIDEO_QUALITIES` /
`AUDIO_QUALITIES` in `ytdl_core.py` and both the on-screen menu and the yt-dlp
format string update together.

## License

MIT License — see [LICENSE](LICENSE).
