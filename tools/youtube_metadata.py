import requests
import os
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def extract_video_id(url):
    query = urlparse(url)
    if query.hostname == "youtu.be":
        return query.path[1:]
    if query.hostname in ["www.youtube.com", "youtube.com"]:
        if query.path == "/watch":
            return parse_qs(query.query).get("v", [None])[0]
        if query.path.startswith("/embed/"):
            return query.path.split("/")[2]
        if query.path.startswith("/v/"):
            return query.path.split("/")[2]
    return None

def fetch_video_metadata(url):
    video_id = extract_video_id(url)
    if not video_id:
        return None

    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={video_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(api_url)

    if response.status_code != 200:
        return None

    data = response.json()
    if not data["items"]:
        return None

    item = data["items"][0]
    snippet = item["snippet"]
    stats = item["statistics"]

    return {
        "title": snippet["title"],
        "description": snippet["description"],
        "thumbnail_url": snippet["thumbnails"]["high"]["url"],
        "channel_title": snippet["channelTitle"],
        "view_count": stats.get("viewCount", "N/A"),
        "like_count": stats.get("likeCount", "N/A"),
        "video_id": video_id,
    }
