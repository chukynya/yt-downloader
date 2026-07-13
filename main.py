"""YouTube MP3 & MP4 downloader — interactive command-line app.

A thin I/O layer over ytdl_core: it builds the yt-dlp options, runs the
downloads, and drives the interactive menu. The pure logic (URL cleaning,
quality tables, format codes, environment checks) lives in ytdl_core.py and is
unit-tested there.

Run it with:  python main.py
"""

import os

try:
    import yt_dlp
except ModuleNotFoundError:
    raise SystemExit(
        "yt-dlp is not installed.\n"
        "Install the dependencies first:  pip install -r requirements.txt"
    )

from ytdl_core import (
    AUDIO_QUALITIES,
    DOWNLOAD_DIR,
    RECOMMENDED_AUDIO,
    RECOMMENDED_VIDEO,
    VIDEO_QUALITIES,
    check_ffmpeg,
    check_js_runtime,
    clean_youtube_url,
    get_audio_format_code,
    get_video_format_code,
    validate_url,
)


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
