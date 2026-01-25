import yt_dlp
import os
import shutil
import sys

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    return shutil.which('ffmpeg') is not None

def check_js_runtime():
    """Check if a JavaScript runtime is available"""
    runtimes = ['deno', 'node', 'nodejs', 'bun']
    for runtime in runtimes:
        if shutil.which(runtime):
            return runtime
    return None

def get_ydl_base_opts():
    """Get base yt-dlp options with proper extractor settings"""
    opts = {
        'quiet': False,
        'no_warnings': False,
        # Use more compatible extraction methods
        'extractor_args': {
            'youtube': {
                # Use android client which is more reliable
                'player_client': ['android', 'web'],
                # Skip formats that require SABR streaming
                'player_skip': ['webpage', 'configs'],
            }
        },
        # Prefer direct HTTP formats over HLS/m3u8
        'format_sort': ['res', 'ext:mp4:m4a:mp3', 'proto:https'],
    }
    return opts

def display_main_menu():
    """Display main menu"""
    print("\n=== What would you like to download? ===")
    print("1. Video (MP4)")
    print("2. Audio only (MP3)")
    print("3. Quit")
    print("========================================\n")

def display_video_quality_options():
    """Display available video quality options"""
    print("\n=== Video Quality Options ===")
    print("1. Best available quality")
    print("2. 1080p (Full HD)")
    print("3. 720p (HD)")
    print("4. 480p")
    print("5. 360p")
    print("6. Lowest quality (saves data)")
    print("=============================\n")

def display_audio_quality_options():
    """Display available audio quality options"""
    print("\n=== Audio Quality Options ===")
    print("1. Best quality (320kbps if available)")
    print("2. High quality (256kbps)")
    print("3. Medium quality (192kbps)")
    print("4. Low quality (128kbps)")
    print("=============================\n")

def get_video_format_code(choice, has_ffmpeg=True):
    """Map user choice to yt-dlp format code for video"""
    if has_ffmpeg:
        # With FFmpeg, we can merge best video + best audio
        # Using format_sort approach for better compatibility
        format_map = {
            '1': 'bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b',  # Best video + best audio
            '2': 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]',
            '3': 'bv*[height<=720][ext=mp4]+ba[ext=m4a]/bv*[height<=720]+ba/b[height<=720]',
            '4': 'bv*[height<=480][ext=mp4]+ba[ext=m4a]/bv*[height<=480]+ba/b[height<=480]',
            '5': 'bv*[height<=360][ext=mp4]+ba[ext=m4a]/bv*[height<=360]+ba/b[height<=360]',
            '6': 'wv*[ext=mp4]+wa[ext=m4a]/wv*+wa/w',  # Worst video + audio
        }
    else:
        # Without FFmpeg, use formats that already have both video and audio
        format_map = {
            '1': 'b[ext=mp4]/b',
            '2': 'b[height<=1080][ext=mp4]/b[height<=1080]',
            '3': 'b[height<=720][ext=mp4]/b[height<=720]',
            '4': 'b[height<=480][ext=mp4]/b[height<=480]',
            '5': 'b[height<=360][ext=mp4]/b[height<=360]',
            '6': 'w[ext=mp4]/w',
        }
    return format_map.get(choice, format_map['1'])

def get_audio_format_code():
    """Get format code for audio-only download"""
    return 'ba[ext=m4a]/ba/b'  # Best audio, prefer m4a

def progress_hook(d):
    """Display download progress"""
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', 'N/A')
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')
        print(f"\rProgress: {percent} | Speed: {speed} | ETA: {eta}    ", end='', flush=True)
    elif d['status'] == 'finished':
        print(f"\nDownload finished, processing...")

def download_video(url, format_code, output_path, has_ffmpeg=True):
    """Download video with specified format"""
    ydl_opts = get_ydl_base_opts()
    ydl_opts.update({
        'format': format_code,
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        # Prefer HTTPS over m3u8/HLS to avoid fragment issues
        'format_sort': ['proto:https', 'res', 'ext:mp4:m4a'],
    })
    
    if has_ffmpeg:
        ydl_opts['merge_output_format'] = 'mp4'
    
    print(f"\nDownloading to: {output_path}")
    print("Starting video download...\n")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("\n✓ Video download completed successfully!")
        return True
    except Exception as e:
        print(f"\n✗ Error during download: {str(e)}")
        return False

def download_audio(url, quality_choice, output_path, has_ffmpeg=True):
    """Download audio only and optionally convert to MP3"""
    ydl_opts = get_ydl_base_opts()
    ydl_opts.update({
        'format': get_audio_format_code(),
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'format_sort': ['proto:https', 'abr', 'ext:m4a:mp3'],
    })
    
    # Audio quality bitrate mapping
    quality_map = {
        '1': '320',
        '2': '256',
        '3': '192',
        '4': '128',
    }
    target_bitrate = quality_map.get(quality_choice, '320')
    
    if has_ffmpeg:
        # Convert to MP3 with specified bitrate
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': target_bitrate,
        }]
        ydl_opts['extract_audio'] = True
    
    print(f"\nDownloading to: {output_path}")
    if has_ffmpeg:
        print(f"Converting to MP3 at {target_bitrate}kbps...")
    else:
        print("Note: Without FFmpeg, audio will be saved in original format (m4a)")
    print("Starting audio download...\n")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("\n✓ Audio download completed successfully!")
        return True
    except Exception as e:
        print(f"\n✗ Error during download: {str(e)}")
        return False

def validate_url(url):
    """Validate if URL is a valid YouTube URL"""
    valid_domains = ['youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com']
    return any(domain in url for domain in valid_domains)

def main():
    print("=" * 50)
    print("    YouTube MP3 & MP4 Downloader")
    print("=" * 50)
    
    # Check for FFmpeg
    has_ffmpeg = check_ffmpeg()
    if not has_ffmpeg:
        print("\n⚠ FFmpeg not found!")
        print("  - Video: Quality options may be limited")
        print("  - Audio: Will be saved as M4A instead of MP3")
        print("  Install FFmpeg: https://ffmpeg.org/download.html")
        print("  Or use: winget install FFmpeg")
    else:
        print("\n✓ FFmpeg detected - full features available!")
    
    # Check for JavaScript runtime
    js_runtime = check_js_runtime()
    if not js_runtime:
        print("\n⚠ No JavaScript runtime found!")
        print("  Some videos may have limited format options.")
        print("  Install one of: deno, node, or bun")
        print("  Recommended: winget install DenoLand.Deno")
    else:
        print(f"✓ JavaScript runtime detected: {js_runtime}")
    
    # Setup download folder
    output_path = os.path.join(os.getcwd(), 'downloads')
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    while True:
        # Get YouTube URL from user
        url = input("\nEnter YouTube URL (or 'q' to quit): ").strip()
        
        if url.lower() == 'q':
            print("Goodbye!")
            break
        
        if not url:
            print("Please enter a valid URL.")
            continue
        
        if not validate_url(url):
            print("Please enter a valid YouTube URL.")
            continue
        
        # Display main menu
        display_main_menu()
        download_type = input("Select option (1-3): ").strip()
        
        if download_type == '3':
            print("Goodbye!")
            break
        elif download_type == '1':
            # Video download
            display_video_quality_options()
            quality_choice = input("Select quality option (1-6): ").strip()
            
            if quality_choice not in ['1', '2', '3', '4', '5', '6']:
                print("Invalid choice. Using best available quality.")
                quality_choice = '1'
            
            format_code = get_video_format_code(quality_choice, has_ffmpeg)
            download_video(url, format_code, output_path, has_ffmpeg)
            
        elif download_type == '2':
            # Audio download
            display_audio_quality_options()
            quality_choice = input("Select quality option (1-4): ").strip()
            
            if quality_choice not in ['1', '2', '3', '4']:
                print("Invalid choice. Using best quality.")
                quality_choice = '1'
            
            download_audio(url, quality_choice, output_path, has_ffmpeg)
        else:
            print("Invalid option. Please try again.")
            continue
        
        # Ask if user wants to download another
        another = input("\nDownload another? (y/n): ").strip().lower()
        if another != 'y':
            print("Goodbye!")
            break

if __name__ == "__main__":
    main()
