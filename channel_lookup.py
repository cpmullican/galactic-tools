#!/usr/bin/env python3
"""Channel lookup for acquisition screening using YouTube Data API v3."""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

API_BASE = "https://www.googleapis.com/youtube/v3"


def _error(msg: str, code: int = 1) -> None:
    payload = {"error": msg}
    print(json.dumps(payload, indent=2))
    sys.exit(code)


def _get_api_key() -> str:
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        _error("YOUTUBE_API_KEY environment variable not set", 2)
    return key


def _request(endpoint: str, params: Dict[str, str]) -> Dict:
    params = dict(params)
    params["key"] = _get_api_key()
    resp = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=20)
    if resp.status_code != 200:
        try:
            data = resp.json()
            msg = data.get("error", {}).get("message")
        except Exception:
            msg = resp.text
        _error(f"YouTube API error ({resp.status_code}): {msg}", 3)
    return resp.json()


def _parse_channel_input(raw: str) -> Dict[str, str]:
    raw = raw.strip()

    # Direct channel ID
    if re.fullmatch(r"UC[0-9A-Za-z_-]{20,}", raw):
        return {"type": "id", "value": raw}

    # Handle like @name
    if raw.startswith("@"):  # handle
        return {"type": "handle", "value": raw.lstrip("@")}

    # URL patterns
    m = re.search(r"youtube\.com/channel/([0-9A-Za-z_-]+)", raw)
    if m:
        return {"type": "id", "value": m.group(1)}

    m = re.search(r"youtube\.com/@([0-9A-Za-z_.-]+)", raw)
    if m:
        return {"type": "handle", "value": m.group(1)}

    m = re.search(r"youtube\.com/user/([0-9A-Za-z_.-]+)", raw)
    if m:
        return {"type": "username", "value": m.group(1)}

    m = re.search(r"youtube\.com/c/([0-9A-Za-z_.-]+)", raw)
    if m:
        return {"type": "custom", "value": m.group(1)}

    # Fallback: treat as handle or channel name
    return {"type": "query", "value": raw.lstrip("@")}


def _search_channel_id(query: str) -> Optional[str]:
    data = _request(
        "search",
        {
            "part": "snippet",
            "type": "channel",
            "q": query,
            "maxResults": "1",
        },
    )
    items = data.get("items", [])
    if not items:
        return None
    return items[0]["snippet"]["channelId"]


def _resolve_channel_id(parsed: Dict[str, str]) -> Optional[str]:
    if parsed["type"] == "id":
        return parsed["value"]
    if parsed["type"] == "username":
        data = _request(
            "channels",
            {"part": "id", "forUsername": parsed["value"], "maxResults": "1"},
        )
        items = data.get("items", [])
        if items:
            return items[0]["id"]
        return None

    # For handles/custom/query, use search
    return _search_channel_id(parsed["value"])


def _parse_iso_date(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _niche_guess(description: str, keywords: str) -> str:
    text = f"{description} {keywords}".lower()

    buckets = {
        "Gaming": ["game", "gaming", "playthrough", "minecraft", "fortnite", "roblox", "esports"],
        "Tech": ["tech", "review", "gadget", "software", "hardware", "programming", "ai", "coding"],
        "Beauty": ["makeup", "beauty", "skincare", "cosmetic", "fashion"],
        "Fitness": ["workout", "fitness", "gym", "training", "yoga", "running"],
        "Education": ["tutorial", "learn", "lesson", "course", "education", "how to"],
        "Finance": ["finance", "invest", "stock", "crypto", "money", "business"],
        "Food": ["recipe", "cook", "cooking", "kitchen", "food"],
        "Travel": ["travel", "trip", "vlog", "tour", "adventure"],
        "Music": ["music", "song", "cover", "producer", "band"],
        "Entertainment": ["vlog", "comedy", "prank", "challenge", "reaction"],
    }

    scores = {k: 0 for k in buckets}
    for niche, words in buckets.items():
        for w in words:
            if w in text:
                scores[niche] += 1

    best = max(scores.items(), key=lambda x: x[1])
    return best[0] if best[1] > 0 else "Unknown"


def _estimate_monthly_views(avg_views: Optional[float], dates: List[datetime]) -> Optional[int]:
    if not avg_views or len(dates) < 2:
        return None
    dates_sorted = sorted(dates)
    total_days = (dates_sorted[-1] - dates_sorted[0]).days
    if total_days <= 0:
        return None
    avg_days_between = total_days / (len(dates_sorted) - 1)
    if avg_days_between <= 0:
        return None
    uploads_per_month = 30.0 / avg_days_between
    return int(avg_views * uploads_per_month)


def _fallback_monthly_views(total_views: int, created: Optional[datetime]) -> Optional[int]:
    if not created:
        return None
    now = datetime.now(timezone.utc)
    age_days = (now - created).days
    if age_days <= 0:
        return None
    age_months = max(age_days / 30.0, 1.0)
    return int(total_views / age_months)


def _get_channel_metrics(channel_id: str) -> Dict:
    channel = _request(
        "channels",
        {
            "part": "snippet,contentDetails,statistics,brandingSettings",
            "id": channel_id,
        },
    )
    items = channel.get("items", [])
    if not items:
        _error("Channel not found", 4)

    ch = items[0]
    snippet = ch.get("snippet", {})
    stats = ch.get("statistics", {})
    content = ch.get("contentDetails", {})
    branding = ch.get("brandingSettings", {}).get("channel", {})

    channel_name = snippet.get("title", "")
    description = snippet.get("description", "")
    keywords = branding.get("keywords", "")

    subscriber_count = int(stats.get("subscriberCount", 0))
    total_views = int(stats.get("viewCount", 0))
    video_count = int(stats.get("videoCount", 0))

    created_date = _parse_iso_date(snippet.get("publishedAt", ""))

    uploads_playlist = content.get("relatedPlaylists", {}).get("uploads")
    last_upload_date = None
    avg_views_per_video = None
    estimated_monthly_views = None

    if uploads_playlist:
        playlist_data = _request(
            "playlistItems",
            {
                "part": "snippet,contentDetails",
                "playlistId": uploads_playlist,
                "maxResults": "10",
            },
        )
        items = playlist_data.get("items", [])
        video_ids = []
        upload_dates = []
        for item in items:
            snippet_i = item.get("snippet", {})
            vid = snippet_i.get("resourceId", {}).get("videoId")
            if vid:
                video_ids.append(vid)
            published = snippet_i.get("publishedAt")
            dt = _parse_iso_date(published) if published else None
            if dt:
                upload_dates.append(dt)

        if upload_dates:
            last_upload_date = max(upload_dates)

        if video_ids:
            vids = _request(
                "videos",
                {"part": "statistics", "id": ",".join(video_ids)},
            )
            view_counts = []
            for v in vids.get("items", []):
                stats_v = v.get("statistics", {})
                try:
                    view_counts.append(int(stats_v.get("viewCount", 0)))
                except Exception:
                    continue

            if view_counts:
                avg_views_per_video = sum(view_counts) / len(view_counts)
                estimated_monthly_views = _estimate_monthly_views(avg_views_per_video, upload_dates)

    if estimated_monthly_views is None:
        estimated_monthly_views = _fallback_monthly_views(total_views, created_date)

    niche_guess = _niche_guess(description, keywords)

    return {
        "channel_name": channel_name,
        "subscriber_count": subscriber_count,
        "total_views": total_views,
        "video_count": video_count,
        "channel_created_date": created_date.isoformat() if created_date else None,
        "last_upload_date": last_upload_date.isoformat() if last_upload_date else None,
        "avg_views_per_video": round(avg_views_per_video, 2) if avg_views_per_video else None,
        "estimated_monthly_views": estimated_monthly_views,
        "niche_guess": niche_guess,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lookup YouTube channel metrics for acquisition screening",
    )
    parser.add_argument("input", help="Channel URL, handle, or channel ID")

    args = parser.parse_args()

    parsed = _parse_channel_input(args.input)
    channel_id = _resolve_channel_id(parsed)
    if not channel_id:
        _error("Unable to resolve channel ID from input", 5)

    data = _get_channel_metrics(channel_id)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
