import os
import json
from youtube_transcript_api import YouTubeTranscriptApi  # Changed import

CACHE_FILE = "transcript_cache.json"

# Load existing cache
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        transcript_cache = json.load(f)
else:
    transcript_cache = {}

def get_video_id(url):
    import re
    match = re.search(r"v=([\w-]+)", url)
    return match.group(1) if match else None

def get_youtube_transcript(url):
    video_id = get_video_id(url)
    if video_id in transcript_cache:
        print(f"[Cache] Transcript for {video_id} loaded from cache.")
        return transcript_cache[video_id]
    
    try:
        # Get transcript using the YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Extract just the text from each transcript segment
        transcript = [item['text'] for item in transcript_list]
        
        # Cache the transcript
        transcript_cache[video_id] = transcript
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(transcript_cache, f, ensure_ascii=False, indent=2)
        
        return transcript
    except Exception as e:
        print(f"Error getting transcript: {e}")
        return []
