import os
from googleapiclient.discovery import build

# Set up the YouTube Data API client
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # Ensure you've set this in your environment variables

def fetch_video_metadata(video_url: str):
    """
    Fetch metadata for a YouTube video given its URL.
    Returns a dictionary with title, description, thumbnail URL, and views count.
    """
    video_id = video_url.split("v=")[-1]
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    request = youtube.videos().list(part="snippet,statistics", id=video_id)
    response = request.execute()

    if response["items"]:
        video_info = response["items"][0]
        title = video_info["snippet"]["title"]
        description = video_info["snippet"]["description"]
        thumbnail_url = video_info["snippet"]["thumbnails"]["high"]["url"]
        views = video_info["statistics"]["viewCount"]
        return {
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "views": views
        }
    else:
        return None
