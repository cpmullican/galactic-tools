#!/usr/bin/env python3
"""
YouTube Data API integration
Ported from galactic-website/src/lib/youtube.ts
"""
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import requests

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


@dataclass
class VideoData:
    published_at: datetime
    view_count: int
    is_short: bool
    duration: str


@dataclass
class ChannelData:
    id: str
    username: str
    title: str
    description: str
    thumbnail_url: Optional[str]
    subscribers: int
    total_views: int
    video_count: int
    average_views: int
    join_date: str
    country: Optional[str]
    recent_videos: List[VideoData]


def get_api_key() -> str:
    """Get YouTube API key from environment."""
    key = os.environ.get("YOUTUBE_API_KEY") or os.environ.get("VITE_YOUTUBE_API_KEY")
    if not key:
        raise ValueError("YOUTUBE_API_KEY environment variable not set")
    return key


def extract_channel_identifier(input_str: str, api_key: str) -> Optional[str]:
    """Extract channel ID from various URL formats or resolve handle/username."""
    input_str = input_str.strip()
    
    # Direct channel ID
    if re.match(r'^UC[\w-]{22}$', input_str):
        return input_str
    
    # Parse URL
    if 'youtube.com' in input_str or 'youtu.be' in input_str:
        # /channel/UC...
        match = re.search(r'/channel/(UC[\w-]{22})', input_str)
        if match:
            return match.group(1)
        
        # /@handle
        match = re.search(r'/@([\w.-]+)', input_str)
        if match:
            return resolve_handle(match.group(1), api_key)
        
        # /c/customurl
        match = re.search(r'/c/([\w.-]+)', input_str)
        if match:
            return resolve_custom_url(match.group(1), api_key)
        
        # /user/username
        match = re.search(r'/user/([\w.-]+)', input_str)
        if match:
            return resolve_username(match.group(1), api_key)
    
    # Try as handle (with or without @)
    identifier = input_str.lstrip('@')
    return resolve_any_identifier(identifier, api_key)


def resolve_handle(handle: str, api_key: str) -> Optional[str]:
    """Resolve @handle to channel ID."""
    try:
        resp = requests.get(f"{YOUTUBE_API_BASE}/channels", params={
            "forHandle": handle,
            "part": "id",
            "key": api_key
        })
        data = resp.json()
        if data.get("items"):
            return data["items"][0]["id"]
    except Exception:
        pass
    return None


def resolve_username(username: str, api_key: str) -> Optional[str]:
    """Resolve legacy username to channel ID."""
    try:
        resp = requests.get(f"{YOUTUBE_API_BASE}/channels", params={
            "forUsername": username,
            "part": "id",
            "key": api_key
        })
        data = resp.json()
        if data.get("items"):
            return data["items"][0]["id"]
    except Exception:
        pass
    return None


def resolve_custom_url(custom_url: str, api_key: str) -> Optional[str]:
    """Resolve custom URL to channel ID."""
    # Try as username first
    result = resolve_username(custom_url, api_key)
    if result:
        return result
    # Try as handle
    return resolve_handle(custom_url, api_key)


def resolve_any_identifier(identifier: str, api_key: str) -> Optional[str]:
    """Try all resolution methods."""
    for resolver in [resolve_handle, resolve_username, resolve_custom_url]:
        result = resolver(identifier, api_key)
        if result:
            return result
    return None


def parse_duration_to_seconds(duration: str) -> int:
    """Parse ISO 8601 duration to seconds."""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def is_short(duration: str) -> bool:
    """Check if video is a Short (60 seconds or less)."""
    seconds = parse_duration_to_seconds(duration)
    return seconds <= 60


def get_channel_data(channel_input: str) -> ChannelData:
    """
    Fetch channel data from YouTube API.
    
    Args:
        channel_input: Channel URL, @handle, username, or channel ID
        
    Returns:
        ChannelData with all metrics
    """
    api_key = get_api_key()
    
    # Resolve to channel ID
    channel_id = extract_channel_identifier(channel_input, api_key)
    if not channel_id:
        raise ValueError(f"Could not find channel: {channel_input}")
    
    # Get channel details
    resp = requests.get(f"{YOUTUBE_API_BASE}/channels", params={
        "id": channel_id,
        "part": "snippet,statistics,contentDetails",
        "key": api_key
    })
    data = resp.json()
    
    if not data.get("items"):
        raise ValueError(f"Channel not found: {channel_id}")
    
    channel = data["items"][0]
    snippet = channel.get("snippet", {})
    stats = channel.get("statistics", {})
    
    # Get recent videos (last year, up to 50)
    one_year_ago = (datetime.now() - timedelta(days=365)).isoformat() + "Z"
    
    resp = requests.get(f"{YOUTUBE_API_BASE}/search", params={
        "channelId": channel_id,
        "part": "snippet",
        "order": "date",
        "type": "video",
        "maxResults": "50",
        "publishedAfter": one_year_ago,
        "key": api_key
    })
    videos_data = resp.json()
    
    video_ids = [item["id"]["videoId"] for item in videos_data.get("items", []) if item.get("id", {}).get("videoId")]
    
    recent_videos = []
    if video_ids:
        # Get video details
        resp = requests.get(f"{YOUTUBE_API_BASE}/videos", params={
            "id": ",".join(video_ids),
            "part": "contentDetails,statistics",
            "key": api_key
        })
        video_details = resp.json()
        
        for item in video_details.get("items", []):
            duration = item.get("contentDetails", {}).get("duration", "PT0S")
            view_count = int(item.get("statistics", {}).get("viewCount", 0))
            published_at = None
            
            # Find matching snippet for publish date
            for search_item in videos_data.get("items", []):
                if search_item.get("id", {}).get("videoId") == item["id"]:
                    published_at = search_item.get("snippet", {}).get("publishedAt")
                    break
            
            if published_at:
                recent_videos.append(VideoData(
                    published_at=datetime.fromisoformat(published_at.replace("Z", "+00:00")),
                    view_count=view_count,
                    is_short=is_short(duration),
                    duration=duration
                ))
    
    # Calculate stats
    subscribers = int(stats.get("subscriberCount", 0))
    total_views = int(stats.get("viewCount", 0))
    video_count = int(stats.get("videoCount", 0))
    average_views = total_views // video_count if video_count > 0 else 0
    
    # Get username from custom URL
    custom_url = snippet.get("customUrl", "")
    username = custom_url.lstrip("@") if custom_url else snippet.get("title", "").lower().replace(" ", "")
    
    thumbnail = snippet.get("thumbnails", {}).get("default", {}).get("url")
    
    return ChannelData(
        id=channel_id,
        username=username,
        title=snippet.get("title", ""),
        description=snippet.get("description", ""),
        thumbnail_url=thumbnail,
        subscribers=subscribers,
        total_views=total_views,
        video_count=video_count,
        average_views=average_views,
        join_date=snippet.get("publishedAt", ""),
        country=snippet.get("country"),
        recent_videos=recent_videos
    )


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) > 1:
        try:
            data = get_channel_data(sys.argv[1])
            print(f"Channel: {data.title}")
            print(f"Subscribers: {data.subscribers:,}")
            print(f"Total Views: {data.total_views:,}")
            print(f"Videos: {data.video_count}")
            print(f"Avg Views: {data.average_views:,}")
            print(f"Recent videos: {len(data.recent_videos)}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python youtube_api.py <channel_url_or_handle>")
