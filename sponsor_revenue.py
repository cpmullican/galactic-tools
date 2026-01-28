#!/usr/bin/env python3
"""
Sponsorship Revenue Calculator

Ported from Galactic Media Group's internal channel evaluation tool.
Estimates potential brand deal revenue based on channel metrics.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple


@dataclass
class VideoData:
    """Represents a single video's metrics."""
    published_at: datetime
    view_count: int
    is_short: bool = False
    duration_seconds: int = 0


@dataclass
class ChannelMetrics:
    """Channel-level metrics for revenue calculation."""
    subscribers: int
    total_views: int
    video_count: int
    average_views: int
    monthly_views: Optional[int] = None
    recent_videos: Optional[List[VideoData]] = None


@dataclass
class RevenueEstimate:
    """Revenue estimation results."""
    brand_deal_rate: int  # Per-integration rate
    annual_uploads: int
    yearly_potential: int
    v30_average: int  # 30-day view average
    confidence: str  # "high", "medium", "low"
    notes: List[str]


def calculate_brand_deal_rate(average_views: int) -> int:
    """
    Calculate estimated brand deal rate per integration.
    
    Formula: rate = a * (views ^ b)
    Where a = 0.0685, b = 0.961
    
    This formula was derived from market data on sponsorship rates
    across various channel sizes in the business/education niche.
    
    Args:
        average_views: Average views per video
        
    Returns:
        Estimated rate per brand integration (USD)
    """
    if average_views <= 0:
        return 0
    
    a = 0.0685
    b = 0.961
    rate = a * (average_views ** b)
    return round(rate)


def calculate_v30(videos: List[VideoData]) -> int:
    """
    Calculate 30-day view average (V30) across recent videos.
    
    For videos under 30 days old: extrapolates linearly
    For videos over 30 days old: assumes 60% of views came in first 30 days
    
    Args:
        videos: List of VideoData objects (should be recent, non-short videos)
        
    Returns:
        Average estimated 30-day views per video
    """
    if not videos:
        return 0
    
    # Filter out shorts
    regular_videos = [v for v in videos if not v.is_short][:25]
    
    if not regular_videos:
        return 0
    
    now = datetime.now()
    total_v30 = 0
    count = 0
    
    for video in regular_videos:
        days_since_publish = (now - video.published_at).days
        
        # Skip invalid dates or very new videos
        if days_since_publish <= 0:
            continue
        if days_since_publish < 1:
            continue
            
        if days_since_publish < 30:
            # Extrapolate linearly for newer videos
            estimated_v30 = (video.view_count / days_since_publish) * 30
        else:
            # For older videos, assume 60% of views in first 30 days
            estimated_v30 = video.view_count * 0.6
        
        if estimated_v30 >= 0 and math.isfinite(estimated_v30):
            total_v30 += estimated_v30
            count += 1
    
    if count == 0:
        return 0
    
    return round(total_v30 / count)


def calculate_annual_upload_volume(videos: List[VideoData]) -> int:
    """
    Estimate annual upload frequency using weighted average of recent intervals.
    
    Uses exponential decay weighting (lambda=2) to favor recent upload patterns.
    Caps individual intervals at 30 days to prevent large gaps from skewing.
    
    Args:
        videos: List of VideoData objects sorted by date (newest first)
        
    Returns:
        Estimated uploads per year
    """
    if not videos or len(videos) < 2:
        return 0
    
    now = datetime.now()
    
    # Filter out shorts and future dates, take up to 25 recent videos
    regular_videos = [
        v for v in videos 
        if not v.is_short and v.published_at <= now
    ]
    regular_videos.sort(key=lambda v: v.published_at, reverse=True)
    regular_videos = regular_videos[:25]
    
    if len(regular_videos) < 2:
        return 0
    
    # Calculate intervals between consecutive uploads
    intervals = []
    max_interval = 30  # Cap at 30 days to prevent outlier skew
    
    for i in range(len(regular_videos) - 1):
        days_diff = (regular_videos[i].published_at - regular_videos[i + 1].published_at).days
        capped_diff = min(days_diff, max_interval)
        intervals.append(capped_diff)
    
    if not intervals:
        return 0
    
    # Weighted average with exponential decay (recency bias)
    lambda_decay = 2
    weighted_sum = 0
    total_weight = 0
    
    for i, interval in enumerate(intervals):
        weight = math.exp(-i / lambda_decay)
        weighted_sum += interval * weight
        total_weight += weight
    
    if total_weight == 0:
        return 0
    
    weighted_avg_interval = weighted_sum / total_weight
    
    if weighted_avg_interval <= 0:
        return 365  # Daily uploads
    
    return round(365 / weighted_avg_interval)


def calculate_yearly_potential(
    brand_deal_rate: int,
    annual_uploads: int,
    integration_rate: float = 0.9
) -> int:
    """
    Calculate potential yearly brand revenue.
    
    Args:
        brand_deal_rate: Rate per integration
        annual_uploads: Estimated uploads per year
        integration_rate: Percentage of videos with integrations (default 90%)
        
    Returns:
        Estimated yearly brand revenue (USD)
    """
    return round(brand_deal_rate * annual_uploads * integration_rate)


def estimate_sponsor_revenue(
    metrics: ChannelMetrics,
    videos: Optional[List[VideoData]] = None
) -> RevenueEstimate:
    """
    Full sponsorship revenue estimation.
    
    Args:
        metrics: Channel-level metrics
        videos: Optional list of recent videos for detailed analysis
        
    Returns:
        RevenueEstimate with all calculated values
    """
    notes = []
    confidence = "high"
    
    # Calculate brand deal rate from average views
    brand_rate = calculate_brand_deal_rate(metrics.average_views)
    notes.append(f"Brand rate based on {metrics.average_views:,} avg views/video")
    
    # Calculate V30 and annual uploads if video data provided
    if videos and len(videos) >= 2:
        v30 = calculate_v30(videos)
        annual_uploads = calculate_annual_upload_volume(videos)
        notes.append(f"Upload frequency from {len(videos)} recent videos")
    else:
        # Fallback estimates
        v30 = metrics.average_views
        # Estimate uploads from total video count and rough channel age
        if metrics.video_count > 0:
            # Assume ~3 year average channel age for rough estimate
            annual_uploads = max(12, min(metrics.video_count // 3, 200))
            notes.append("Upload frequency estimated (no video history)")
            confidence = "medium"
        else:
            annual_uploads = 52  # Weekly default
            confidence = "low"
            notes.append("Using default weekly upload assumption")
    
    # Calculate yearly potential
    yearly_potential = calculate_yearly_potential(brand_rate, annual_uploads)
    
    # Confidence adjustments
    if metrics.subscribers < 100000:
        confidence = "low"
        notes.append("Below 100K subs - rates may vary significantly")
    elif metrics.subscribers < 500000:
        if confidence == "high":
            confidence = "medium"
        notes.append("Mid-tier channel - good market data available")
    else:
        notes.append("Large channel - premium rates likely")
    
    return RevenueEstimate(
        brand_deal_rate=brand_rate,
        annual_uploads=annual_uploads,
        yearly_potential=yearly_potential,
        v30_average=v30,
        confidence=confidence,
        notes=notes
    )


def format_currency(amount: int) -> str:
    """Format as USD currency string."""
    return f"${amount:,}"


def upload_frequency_label(annual_uploads: int) -> str:
    """Convert annual upload count to human-readable frequency."""
    if annual_uploads >= 300:
        return "Daily"
    elif annual_uploads >= 100:
        return "2-3x per week"
    elif annual_uploads >= 45:
        return "Weekly"
    elif annual_uploads >= 24:
        return "Biweekly"
    elif annual_uploads >= 12:
        return "Monthly"
    else:
        return "Less than monthly"


# Example usage and testing
if __name__ == "__main__":
    # Test with sample data
    test_metrics = ChannelMetrics(
        subscribers=500000,
        total_views=100000000,
        video_count=200,
        average_views=150000,
        monthly_views=3000000
    )
    
    result = estimate_sponsor_revenue(test_metrics)
    
    print("=" * 50)
    print("SPONSORSHIP REVENUE ESTIMATE")
    print("=" * 50)
    print(f"Brand deal rate: {format_currency(result.brand_deal_rate)}/integration")
    print(f"Est. annual uploads: {result.annual_uploads} ({upload_frequency_label(result.annual_uploads)})")
    print(f"V30 average: {result.v30_average:,} views")
    print(f"Yearly potential: {format_currency(result.yearly_potential)}")
    print(f"Confidence: {result.confidence}")
    print("\nNotes:")
    for note in result.notes:
        print(f"  • {note}")
