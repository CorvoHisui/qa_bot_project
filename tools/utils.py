import os
import requests
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up the YouTube Data API client
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def extract_video_id(url):
    """Extract the video ID from a YouTube URL."""
    # Handle different URL formats
    parsed_url = urlparse(url)
    if parsed_url.hostname in ('youtu.be',):
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            try:
                return parse_qs(parsed_url.query)['v'][0]
            except (KeyError, IndexError):
                return None
        if parsed_url.path.startswith('/embed/'):
            return parsed_url.path.split('/')[2]
        if parsed_url.path.startswith('/v/'):
            return parsed_url.path.split('/')[2]
    # If nothing matches
    return None

def fetch_video_metadata(video_url: str):
    """
    Fetch metadata for a YouTube video given its URL using direct API requests.
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        return None
        
    # Get YouTube API key from environment
    api_key = os.environ.get("YOUTUBE_API_KEY", YOUTUBE_API_KEY)
    
    if not api_key:
        print("YouTube API key not found. Please check your .env file.")
        return {
            "title": "Video metadata unavailable (API key not configured)",
            "description": "Configure YOUTUBE_API_KEY in your .env file to see video details",
            "thumbnail_url": "",
            "views": "Unknown"
        }
    
    # Make a direct request to the YouTube API
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={video_id}&key={api_key}"
    
    try:
        response = requests.get(url)
        # Convert the response to JSON first
        data = response.json()
        
        # Now access the data as a dictionary
        if "items" in data and data["items"]:
            video_info = data["items"][0]
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
            return {
                "title": "Video not found",
                "description": "The requested video could not be found",
                "thumbnail_url": "",
                "views": "0"
            }
    except Exception as e:
        print(f"Error fetching video metadata: {e}")
        return {
            "title": "Error fetching video data",
            "description": f"An error occurred: {str(e)}",
            "thumbnail_url": "",
            "views": "Unknown"
        }
