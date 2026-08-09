import sys
import json
from yt_dlp import YoutubeDL
from app.services.ingestion_service import extract_youtube_video_id, _choose_caption_track, clean_transcript, _download_caption_text

TEST_URLS = [
    "https://www.youtube.com/watch?v=NAIC9sjBgZA",
    "https://youtube.com/shorts/gxNyPNyvn7M",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=fJ9rUzIMcZQ", # Queen - Bohemian Rhapsody
]

CLIENT_CONFIGS = [
    ("default", {}),
    ("android_web", {"player_client": ["android", "web"]}),
    ("ios_web", {"player_client": ["ios", "web"]}),
    ("mweb_web", {"player_client": ["mweb", "web"]}),
    ("tv_web", {"player_client": ["tv", "web"]}),
]

def test_url(url: str):
    print(f"\n==========================================")
    print(f"Testing URL: {url}")
    video_id = extract_youtube_video_id(url)
    print(f"Extracted video_id: {video_id}")
    
    for label, yt_args in CLIENT_CONFIGS:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignore_no_formats_error": True,
        }
        if yt_args:
            ydl_opts["extractor_args"] = {"youtube": yt_args}

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            subtitles = list((info.get("subtitles") or {}).keys())
            auto_captions = list((info.get("automatic_captions") or {}).keys())
            track = _choose_caption_track(info)
            print(f"  [{label}] Subs: {subtitles} | Auto: {len(auto_captions)} langs | Chosen: {track.get('kind') if track else None}")
        except Exception as e:
            print(f"  [{label}] ERR: {type(e).__name__}: {e}")

if __name__ == "__main__":
    for u in TEST_URLS:
        test_url(u)
