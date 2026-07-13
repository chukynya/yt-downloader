"""Pure, dependency-free logic for the YouTube downloader.

Everything in this module is free of the yt-dlp dependency and does no console
I/O, so it can be imported and unit-tested on its own (see tests/test_core.py).
The yt-dlp option building, the actual downloading, and the interactive CLI all
live in main.py.

The quality menus are driven by the VIDEO_QUALITIES / AUDIO_QUALITIES tables
below: add or reorder a row and both the on-screen menu and the yt-dlp format
code update together, so the two can never drift out of sync.
"""

import re
import shutil
from urllib.parse import urlparse, parse_qs


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

DOWNLOAD_DIR = "downloads"
JS_RUNTIMES = ("deno", "node", "nodejs", "bun")
VALID_YT_DOMAINS = ("youtube.com", "youtu.be")

# Video quality menu. Maps the key the user types -> (label, height cap).
#   height = None -> best available resolution
#   height = 0    -> worst available resolution
#   height = N    -> cap at N pixels tall (e.g. 1080)
# YouTube's ceiling is 8K (4320p); there is nothing above that to offer.
VIDEO_QUALITIES = {
    "1": ("Best available quality", None),
    "2": ("8K Ultra HD (4320p)", 4320),
    "3": ("4K Ultra HD (2160p)", 2160),
    "4": ("1440p (2K / QHD)", 1440),
    "5": ("1080p (Full HD)", 1080),
    "6": ("720p (HD)", 720),
    "7": ("480p", 480),
    "8": ("360p", 360),
    "9": ("Lowest quality (saves data)", 0),
}
RECOMMENDED_VIDEO = "5"

# Audio quality menu. Maps key -> (label, MP3 bitrate in kbps).
# MP3 is capped at 320 kbps by the codec itself — there is no valid MP3 above
# that, so 320 is the maximum offered. (For higher fidelity you would keep the
# original audio stream, which is no longer an MP3.)
AUDIO_QUALITIES = {
    "1": ("Best quality — 320 kbps (MP3 maximum)", "320"),
    "2": ("High quality — 256 kbps", "256"),
    "3": ("Good quality — 192 kbps", "192"),
    "4": ("Standard quality — 160 kbps", "160"),
    "5": ("Low quality — 128 kbps", "128"),
    "6": ("Smallest size — 96 kbps", "96"),
}
RECOMMENDED_AUDIO = "1"


# --------------------------------------------------------------------------- #
# Environment checks
# --------------------------------------------------------------------------- #

def check_ffmpeg() -> bool:
    """Return True if the FFmpeg binary is available on PATH."""
    return shutil.which("ffmpeg") is not None


def check_js_runtime() -> str | None:
    """Return the name of the first available JavaScript runtime, or None."""
    for runtime in JS_RUNTIMES:
        if shutil.which(runtime):
            return runtime
    return None


# --------------------------------------------------------------------------- #
# URL handling
# --------------------------------------------------------------------------- #

def validate_url(url: str) -> bool:
    """Return True if the URL points at a recognised YouTube domain."""
    return any(domain in url for domain in VALID_YT_DOMAINS)


def clean_youtube_url(url: str) -> str:
    """Reduce any YouTube URL to a canonical single-video link.

    Strips playlist / radio / index params (list, start_radio, index, si, ...)
    so only the specific video is downloaded, not an entire playlist or radio
    mix. Handles watch, youtu.be, shorts, embed, live and /v/ forms, plus
    pastes with no scheme. Falls back to the (scheme-normalized) URL if no valid
    11-character video ID can be found — noplaylist=True still guards that case.
    """
    # Prepend a scheme when missing, otherwise urlparse dumps the host into
    # `.path` and we'd silently pass the list param straight through.
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    video_id = None

    if "youtu.be" in host:
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif "youtube.com" in host:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        else:
            match = re.match(r"^/(?:shorts|embed|live|v)/([^/?#]+)", parsed.path)
            if match:
                video_id = match.group(1)

    if video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return f"https://www.youtube.com/watch?v={video_id}"
    return url


# --------------------------------------------------------------------------- #
# Format codes
# --------------------------------------------------------------------------- #

def get_video_format_code(choice: str, has_ffmpeg: bool = True) -> str:
    """Build the yt-dlp format string for the chosen video quality.

    With FFmpeg we can merge the best separate video + audio streams (required
    for anything above 1080p, which YouTube only serves as separate streams).
    Without FFmpeg we fall back to pre-muxed progressive formats, which top out
    around 720p regardless of the resolution requested. Unknown keys fall back
    to the recommended quality.
    """
    _, height = VIDEO_QUALITIES.get(choice, VIDEO_QUALITIES[RECOMMENDED_VIDEO])

    if has_ffmpeg:
        if height is None:                       # best available
            return "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b"
        if height == 0:                          # worst available
            return "wv*[ext=mp4]+wa[ext=m4a]/wv*+wa/w"
        return (
            f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]/"
            f"bv*[height<={height}]+ba/b[height<={height}]"
        )

    # No FFmpeg: use formats that already contain both video and audio.
    if height is None:
        return "b[ext=mp4]/b"
    if height == 0:
        return "w[ext=mp4]/w"
    return f"b[height<={height}][ext=mp4]/b[height<={height}]"


def get_audio_format_code() -> str:
    """Return the yt-dlp format string for an audio-only download."""
    return "ba[ext=m4a]/ba/b"  # best audio, prefer m4a
