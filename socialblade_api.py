#!/usr/bin/env python3
"""
SocialBlade monthly views scraper via Firecrawl
Ported from galactic-website/src/lib/socialblade.ts
"""
import os
from typing import Optional
import requests


def get_firecrawl_key() -> str:
    """Get Firecrawl API key from environment."""
    key = os.environ.get("FIRECRAWL_API_KEY") or os.environ.get("VITE_FIRECRAWL_API_KEY")
    if not key:
        raise ValueError("FIRECRAWL_API_KEY environment variable not set")
    return key


def get_monthly_views(username: str) -> Optional[int]:
    """
    Get monthly views from SocialBlade using Firecrawl.
    
    Args:
        username: YouTube channel username/handle (without @)
        
    Returns:
        Monthly views count or None if not found
    """
    api_key = get_firecrawl_key()
    username = username.lower().lstrip("@")
    
    # Try different URL formats
    url_formats = [
        f"https://socialblade.com/youtube/c/{username}",
        f"https://socialblade.com/youtube/@{username}",
        f"https://socialblade.com/youtube/user/{username}",
    ]
    
    for url in url_formats:
        try:
            result = extract_monthly_views(url, api_key)
            if result:
                return result
        except Exception as e:
            print(f"Failed with {url}: {e}")
            continue
    
    return None


def extract_monthly_views(url: str, api_key: str) -> Optional[int]:
    """Extract monthly views using Firecrawl's extract endpoint."""
    try:
        resp = requests.post(
            "https://api.firecrawl.dev/v1/extract",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "urls": [url],
                "prompt": "Extract the monthly views statistic from the specified YouTube user page.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "monthly_views": {
                            "type": "number",
                            "description": "The average monthly views number from the statistics section"
                        }
                    },
                    "required": ["monthly_views"]
                }
            },
            timeout=30
        )
        
        data = resp.json()
        
        if data.get("success") and data.get("data", {}).get("monthly_views"):
            return int(data["data"]["monthly_views"])
        
    except Exception as e:
        print(f"Firecrawl extract error: {e}")
    
    return None


def get_monthly_views_simple(username: str) -> Optional[int]:
    """
    Simpler fallback: scrape SocialBlade directly without Firecrawl.
    Uses basic requests + regex parsing.
    """
    import re
    
    username = username.lower().lstrip("@")
    urls = [
        f"https://socialblade.com/youtube/c/{username}",
        f"https://socialblade.com/youtube/@{username}",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                # Look for monthly views pattern
                # SocialBlade shows it as "X views" in various formats
                text = resp.text
                
                # Try to find monthly views - various patterns
                patterns = [
                    r'Monthly Views[:\s]*([0-9,]+)',
                    r'views per month[:\s]*([0-9,]+)',
                    r'"monthlyViews"[:\s]*"?([0-9,]+)"?',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        views_str = match.group(1).replace(",", "")
                        return int(views_str)
                        
        except Exception as e:
            print(f"Simple scrape failed for {url}: {e}")
            continue
    
    return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        username = sys.argv[1]
        print(f"Looking up monthly views for: {username}")
        
        # Try Firecrawl first
        try:
            views = get_monthly_views(username)
            if views:
                print(f"Monthly views (Firecrawl): {views:,}")
            else:
                print("Firecrawl: No data")
        except ValueError as e:
            print(f"Firecrawl: {e}")
        
        # Try simple scrape
        views = get_monthly_views_simple(username)
        if views:
            print(f"Monthly views (simple): {views:,}")
        else:
            print("Simple scrape: No data")
    else:
        print("Usage: python socialblade_api.py <username>")
