import sys
import json
from yt_dlp import YoutubeDL
from app.services.ingestion_service import extract_youtube_video_id, _choose_caption_track, clean_transcript, _download_caption_text

TEST_URLS = [
    "https://www.youtube.com/watch?v=NAIC9sjBgZA",
    "https://youtube.com/shorts/gxNyPNyvn7M",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
]

def test_url(url: str):
    print(f"\n==========================================")
    print(f"Testing URL: {url}")
    video_id = extract_youtube_video_id(url)
    print(f"Extracted video_id: {video_id}")
    
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
        "extract_flat": False,
        "ignore_no_formats_error": True,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        print(f"Title: {info.get('title')}")
        print(f"Channel: {info.get('uploader') or info.get('channel')}")
        print(f"Duration: {info.get('duration')} sec")
        
        subtitles = list((info.get("subtitles") or {}).keys())
        auto_captions = list((info.get("automatic_captions") or {}).keys())
        print(f"Manual Subtitles available: {subtitles}")
        print(f"Automatic Captions available: {auto_captions}")
        
        track = _choose_caption_track(info)
        if track:
            print(f"Chosen Caption Track: kind={track['kind']}, lang={track['language']}")
            try:
                raw_caption = _download_caption_text(track['url'])
                transcript = clean_transcript(raw_caption)
                word_count = len(transcript.split())
                print(f"SUCCESS: Downloaded caption! Word count: {word_count}")
                print(f"Sample transcript (first 200 chars): {transcript[:200]}...")
            except Exception as e:
                print(f"FAILED to download/clean caption text: {type(e).__name__}: {e}")
        else:
            print("NO CAPTION TRACK CHOSEN (track is None) -> Would fall back to metadata capture.")
            
    except Exception as e:
        print(f"yt-dlp extract_info FAILED: {type(e).__name__}: {e}")

if __name__ == "__main__":
    for u in TEST_URLS:
        test_url(u)
