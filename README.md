# YouTube MP3 & MP4 Downloader

A simple command-line tool to download YouTube videos as MP4 or extract audio as MP3.

## Requirements

- Python 3.8 or higher
- yt-dlp
- FFmpeg (recommended, for MP3 conversion and best video quality)
- Deno or Node.js (recommended, for reliable YouTube extraction)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/yt-downloader.git
cd yt-downloader
```

### 2. Install Python dependencies

```bash
pip install yt-dlp
```

### 3. Install FFmpeg (recommended)

**Windows:**
```bash
winget install FFmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ffmpeg
```

### 4. Install JavaScript runtime (recommended)

**Windows:**
```bash
winget install DenoLand.Deno
```

**macOS/Linux:**
```bash
curl -fsSL https://deno.land/install.sh | sh
```

## Usage

Run the downloader:

```bash
python main.py
```

Follow the prompts to:
1. Enter a YouTube URL
2. Choose between video (MP4) or audio (MP3)
3. Select quality options

Downloaded files will be saved in the `downloads` folder.

## Notes

- Without FFmpeg, audio will be saved as M4A instead of MP3
- Without a JavaScript runtime (Deno/Node), some videos may have limited format options
- The tool supports standard YouTube URLs (youtube.com and youtu.be)

## License

MIT License
