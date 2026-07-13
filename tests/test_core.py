"""Unit tests for ytdl_core — the pure logic of the downloader.

These cover the parts most likely to break on a future edit: the URL cleaner
and the quality tables / format codes. They need no network and no yt-dlp.

Run them with any of:
    python -m unittest discover -s tests -t .
    python tests/test_core.py
"""

import os
import sys
import unittest

# Make the repo root importable regardless of how the tests are launched.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ytdl_core as core


class CleanYouTubeURL(unittest.TestCase):
    CANONICAL = "https://www.youtube.com/watch?v=c-mubgIuL60"

    def test_strips_playlist_and_radio_params(self):
        cases = [
            "https://www.youtube.com/watch?v=c-mubgIuL60&list=RDc-mubgIuL60&start_radio=1",
            "https://youtu.be/c-mubgIuL60?si=abc&list=RDx",
            "www.youtube.com/watch?v=c-mubgIuL60&list=RDx",          # no scheme
            "https://m.youtube.com/watch?v=c-mubgIuL60&t=42",        # mobile + timestamp
            "https://www.youtube.com/shorts/c-mubgIuL60",
            "https://www.youtube.com/live/c-mubgIuL60?feature=share",
            "https://www.youtube.com/embed/c-mubgIuL60",
        ]
        for url in cases:
            with self.subTest(url=url):
                self.assertEqual(core.clean_youtube_url(url), self.CANONICAL)

    def test_already_clean_url_is_unchanged(self):
        self.assertEqual(core.clean_youtube_url(self.CANONICAL), self.CANONICAL)

    def test_non_youtube_url_passes_through(self):
        url = "https://example.com/foo?bar=1"
        self.assertEqual(core.clean_youtube_url(url), url)


class ValidateURL(unittest.TestCase):
    def test_accepts_youtube_domains(self):
        for url in (
            "https://www.youtube.com/watch?v=x",
            "https://youtu.be/x",
            "https://m.youtube.com/watch?v=x",
        ):
            with self.subTest(url=url):
                self.assertTrue(core.validate_url(url))

    def test_rejects_other_domains(self):
        self.assertFalse(core.validate_url("https://vimeo.com/123"))


class VideoFormatCodes(unittest.TestCase):
    def test_every_menu_key_produces_a_format(self):
        for key in core.VIDEO_QUALITIES:
            for ffmpeg in (True, False):
                with self.subTest(key=key, ffmpeg=ffmpeg):
                    self.assertTrue(core.get_video_format_code(key, ffmpeg))

    def test_height_cap_is_applied(self):
        for key, (_, height) in core.VIDEO_QUALITIES.items():
            if isinstance(height, int) and height > 0:
                code = core.get_video_format_code(key, has_ffmpeg=True)
                with self.subTest(key=key):
                    self.assertIn(f"height<={height}", code)

    def test_unknown_key_falls_back_to_recommended(self):
        self.assertEqual(
            core.get_video_format_code("does-not-exist"),
            core.get_video_format_code(core.RECOMMENDED_VIDEO),
        )

    def test_ffmpeg_and_non_ffmpeg_differ(self):
        # With FFmpeg we merge separate streams (bv*+ba); without, we don't.
        self.assertNotEqual(
            core.get_video_format_code("5", has_ffmpeg=True),
            core.get_video_format_code("5", has_ffmpeg=False),
        )


class QualityTables(unittest.TestCase):
    def test_mp3_never_exceeds_320(self):
        for key, (_, bitrate) in core.AUDIO_QUALITIES.items():
            with self.subTest(key=key):
                self.assertLessEqual(int(bitrate), 320)

    def test_recommended_keys_exist(self):
        self.assertIn(core.RECOMMENDED_VIDEO, core.VIDEO_QUALITIES)
        self.assertIn(core.RECOMMENDED_AUDIO, core.AUDIO_QUALITIES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
