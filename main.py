"""YouTube MP3 & MP4 downloader.

A small, cross-platform (Linux / Windows / macOS) command-line tool built on
yt-dlp. Paste any YouTube link — playlist and radio parameters are stripped
automatically so only the single requested video is downloaded — then choose an
MP4 video or an MP3 audio download at a selectable quality.

The quality menus are driven by the VIDEO_QUALITIES / AUDIO_QUALITIES tables
below: add or reorder a row there and both the on-screen menu and the yt-dlp
format code update together, so the two can never drift out of sync.
"""

import os
import re
import shutil
from urllib.parse import urlparse, parse_qs

import yt_dlp


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
# yt-dlp option building
# --------------------------------------------------------------------------- #

def get_ydl_base_opts() -> dict:
    """Return the base yt-dlp options shared by every download."""
    return {
        "quiet": False,
        "no_warnings": False,
        # Only ever download the single requested video, never a whole
        # playlist / radio mix even if a `list=` param survives in the URL.
        "noplaylist": True,
        # More compatible extraction methods.
        "extractor_args": {
            "youtube": {
                # The android client is more reliable for format extraction.
                "player_client": ["android", "web"],
                # Skip formats that require SABR streaming.
                "player_skip": ["webpage", "configs"],
            }
        },
        # Prefer direct HTTP formats over HLS / m3u8.
        "format_sort": ["res", "ext:mp4:m4a:mp3", "proto:https"],
    }


def get_video_format_code(choice: str, has_ffmpeg: bool = True) -> str:
    """Build the yt-dlp format string for the chosen video quality.

    With FFmpeg we can merge the best separate video + audio streams (required
    for anything above 1080p, which YouTube only serves as separate streams).
    Without FFmpeg we fall back to pre-muxed progressive formats, which top out
    around 720p regardless of the resolution requested.
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


# --------------------------------------------------------------------------- #
# Menu / prompt helpers
# --------------------------------------------------------------------------- #

def display_main_menu() -> None:
    """Print the top-level download-type menu."""
    print("\n=== What would you like to download? ===")
    print("1. Video (MP4)")
    print("2. Audio only (MP3)")
    print("3. Quit")
    print("========================================\n")


def display_quality_menu(title: str, options: dict, recommended: str) -> None:
    """Print a quality menu from an options table, flagging the recommendation."""
    print(f"\n=== {title} ===")
    for key, (label, _) in options.items():
        marker = "  ← Recommended" if key == recommended else ""
        print(f"{key}. {label}{marker}")
    print("=" * (len(title) + 8))
    print("(Press Enter to accept the recommended option)\n")


def prompt_quality_choice(options: dict, recommended: str) -> str:
    """Prompt for a quality choice, defaulting to the recommendation.

    A bare Enter selects the recommended option; any unrecognised input also
    falls back to it with a notice.
    """
    choice = input(f"Select quality (1-{len(options)}, Enter = recommended): ").strip()
    if choice == "":
        return recommended
    if choice not in options:
        print(f"Invalid choice. Using the recommended option ({recommended}).")
        return recommended
    return choice


def progress_hook(status: dict) -> None:
    """Render download progress on a single refreshing line."""
    if status["status"] == "downloading":
        percent = status.get("_percent_str", "N/A")
        speed = status.get("_speed_str", "N/A")
        eta = status.get("_eta_str", "N/A")
        print(f"\rProgress: {percent} | Speed: {speed} | ETA: {eta}    ", end="", flush=True)
    elif status["status"] == "finished":
        print("\nDownload finished, processing...")


# --------------------------------------------------------------------------- #
# Download
# --------------------------------------------------------------------------- #

def _run_download(url: str, ydl_opts: dict, success_msg: str) -> bool:
    """Run a yt-dlp download with the given options, reporting the outcome."""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"\n✓ {success_msg}")
        return True
    except Exception as exc:  # noqa: BLE001 - surface any yt-dlp/network error to the user
        print(f"\n✗ Error during download: {exc}")
        return False


def download_video(url: str, choice: str, output_path: str, has_ffmpeg: bool = True) -> bool:
    """Download a video at the quality identified by `choice`."""
    ydl_opts = get_ydl_base_opts()
    ydl_opts.update({
        "format": get_video_format_code(choice, has_ffmpeg),
        "outtmpl": os.path.join(output_path, "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        # Prefer HTTPS over m3u8 / HLS to avoid fragment issues.
        "format_sort": ["proto:https", "res", "ext:mp4:m4a"],
    })
    if has_ffmpeg:
        ydl_opts["merge_output_format"] = "mp4"

    print(f"\nDownloading to: {output_path}")
    print("Starting video download...\n")
    return _run_download(url, ydl_opts, "Video download completed successfully!")


def download_audio(url: str, choice: str, output_path: str, has_ffmpeg: bool = True) -> bool:
    """Download audio and, when FFmpeg is present, convert it to MP3."""
    _, bitrate = AUDIO_QUALITIES.get(choice, AUDIO_QUALITIES[RECOMMENDED_AUDIO])

    ydl_opts = get_ydl_base_opts()
    ydl_opts.update({
        "format": get_audio_format_code(),
        "outtmpl": os.path.join(output_path, "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "format_sort": ["proto:https", "abr", "ext:m4a:mp3"],
    })
    if has_ffmpeg:
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": bitrate,
        }]
        ydl_opts["extract_audio"] = True

    print(f"\nDownloading to: {output_path}")
    if has_ffmpeg:
        print(f"Converting to MP3 at {bitrate} kbps...")
    else:
        print("Note: Without FFmpeg, audio will be saved in its original format (m4a)")
    print("Starting audio download...\n")
    return _run_download(url, ydl_opts, "Audio download completed successfully!")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def report_environment() -> bool:
    """Print FFmpeg / JS-runtime status and return whether FFmpeg is available."""
    has_ffmpeg = check_ffmpeg()
    if has_ffmpeg:
        print("\n✓ FFmpeg detected - full features available!")
    else:
        print("\n⚠ FFmpeg not found!")
        print("  - Video: quality above 720p and MP4 merging may be unavailable")
        print("  - Audio: will be saved as M4A instead of MP3")
        print("  Install FFmpeg: https://ffmpeg.org/download.html")
        print("  Windows: winget install Gyan.FFmpeg   |   Fedora: sudo dnf install ffmpeg")

    js_runtime = check_js_runtime()
    if js_runtime:
        print(f"✓ JavaScript runtime detected: {js_runtime}")
    else:
        print("\n⚠ No JavaScript runtime found!")
        print("  Some videos may have limited format options.")
        print("  Install one of: deno, node, or bun")
        print("  Recommended: winget install DenoLand.Deno")

    return has_ffmpeg


def handle_download(url: str, output_path: str, has_ffmpeg: bool) -> bool:
    """Run one download interaction for an already-cleaned URL.

    Returns False when the user chose Quit, True otherwise (so the caller can
    decide whether to keep looping).
    """
    display_main_menu()
    download_type = input("Select option (1-3): ").strip()

    if download_type == "1":
        display_quality_menu("Video Quality Options", VIDEO_QUALITIES, RECOMMENDED_VIDEO)
        choice = prompt_quality_choice(VIDEO_QUALITIES, RECOMMENDED_VIDEO)
        download_video(url, choice, output_path, has_ffmpeg)
    elif download_type == "2":
        display_quality_menu("Audio Quality Options", AUDIO_QUALITIES, RECOMMENDED_AUDIO)
        choice = prompt_quality_choice(AUDIO_QUALITIES, RECOMMENDED_AUDIO)
        download_audio(url, choice, output_path, has_ffmpeg)
    elif download_type == "3":
        return False
    else:
        print("Invalid option. Please try again.")
    return True


def main() -> None:
    print("=" * 50)
    print("    YouTube MP3 & MP4 Downloader")
    print("=" * 50)

    has_ffmpeg = report_environment()

    output_path = os.path.join(os.getcwd(), DOWNLOAD_DIR)
    os.makedirs(output_path, exist_ok=True)

    while True:
        url = input("\nEnter YouTube URL (or 'q' to quit): ").strip()

        if url.lower() == "q":
            break
        if not url:
            print("Please enter a valid URL.")
            continue
        if not validate_url(url):
            print("Please enter a valid YouTube URL.")
            continue

        # Trim playlist / radio params down to the single requested video.
        cleaned = clean_youtube_url(url)
        if cleaned != url:
            print(f"→ Cleaned to single video: {cleaned}")
        url = cleaned

        if not handle_download(url, output_path, has_ffmpeg):
            break

        if input("\nDownload another? (y/n): ").strip().lower() != "y":
            break

    print("Goodbye!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye!")
