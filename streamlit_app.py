#!/usr/bin/env python3
"""Galactic Media Group - YouTube Channel Acquisition Tools"""
import tempfile
import streamlit as st

from channel_valuation import (
    base_multiple_range, clamp, engagement_adjustment,
    growth_proxy_adjustment, valuation_range,
)
from transcript_processor import process_transcript
from sponsor_revenue import (
    ChannelMetrics, VideoData as SponsorVideoData, estimate_sponsor_revenue, 
    format_currency, upload_frequency_label, calculate_brand_deal_rate,
    calculate_annual_upload_volume, calculate_v30,
)

# Check for API availability
YOUTUBE_API_AVAILABLE = False
FIRECRAWL_AVAILABLE = False

try:
    from youtube_api import get_channel_data, get_api_key
    get_api_key()  # Test if key exists
    YOUTUBE_API_AVAILABLE = True
except:
    pass

try:
    from socialblade_api import get_monthly_views, get_firecrawl_key
    get_firecrawl_key()  # Test if key exists
    FIRECRAWL_AVAILABLE = True
except:
    pass


def main():
    st.set_page_config(page_title="Galactic Tools", page_icon="🚀", layout="wide")
    st.title("🚀 Galactic Acquisition Tools")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Channel Analyzer", 
        "💰 Manual Valuation", 
        "💵 Manual Sponsor Rev",
        "📝 Transcripts"
    ])
    
    # === Channel Analyzer (main tool) ===
    with tab1:
        st.header("Channel Analyzer")
        st.caption("Enter a YouTube channel to get full metrics and revenue estimates")
        
        # API Status
        col1, col2 = st.columns(2)
        with col1:
            if YOUTUBE_API_AVAILABLE:
                st.success("✓ YouTube API connected")
            else:
                st.warning("⚠ YouTube API key not set (YOUTUBE_API_KEY)")
        with col2:
            if FIRECRAWL_AVAILABLE:
                st.success("✓ Firecrawl API connected")
            else:
                st.info("ℹ Firecrawl not set (optional, for monthly views)")
        
        st.divider()
        
        channel_input = st.text_input(
            "Channel URL or @handle",
            placeholder="@MrBeast or https://youtube.com/@MrBeast",
            help="Enter channel URL, @handle, or username"
        )
        
        analyze_btn = st.button("Analyze Channel", type="primary", disabled=not YOUTUBE_API_AVAILABLE)
        
        if analyze_btn and channel_input:
            with st.spinner("Fetching channel data..."):
                try:
                    from youtube_api import get_channel_data
                    channel = get_channel_data(channel_input)
                    
                    # Display channel info
                    st.divider()
                    
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if channel.thumbnail_url:
                            st.image(channel.thumbnail_url, width=100)
                    with col2:
                        st.subheader(channel.title)
                        st.caption(f"@{channel.username} • Joined {channel.join_date[:10] if channel.join_date else 'Unknown'}")
                    
                    # Key metrics
                    st.subheader("Channel Metrics")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Subscribers", f"{channel.subscribers:,}")
                    c2.metric("Total Views", f"{channel.total_views:,}")
                    c3.metric("Videos", f"{channel.video_count:,}")
                    c4.metric("Avg Views/Video", f"{channel.average_views:,}")
                    
                    # Get monthly views if Firecrawl available
                    monthly_views = None
                    if FIRECRAWL_AVAILABLE:
                        with st.spinner("Fetching monthly views from SocialBlade..."):
                            try:
                                from socialblade_api import get_monthly_views
                                monthly_views = get_monthly_views(channel.username)
                                if monthly_views:
                                    st.metric("Monthly Views (SocialBlade)", f"{monthly_views:,}")
                            except Exception as e:
                                st.caption(f"Could not fetch monthly views: {e}")
                    
                    # Convert videos for sponsor calculation
                    sponsor_videos = [
                        SponsorVideoData(
                            published_at=v.published_at,
                            view_count=v.view_count,
                            is_short=v.is_short,
                            duration_seconds=0
                        )
                        for v in channel.recent_videos
                    ]
                    
                    # Calculate V30 and upload frequency
                    v30 = calculate_v30(sponsor_videos) if sponsor_videos else channel.average_views
                    annual_uploads = calculate_annual_upload_volume(sponsor_videos) if sponsor_videos else 52
                    
                    st.divider()
                    st.subheader("Upload Analysis")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Recent Videos Analyzed", len([v for v in channel.recent_videos if not v.is_short]))
                    c2.metric("Est. Annual Uploads", annual_uploads)
                    c3.metric("30-Day View Avg (V30)", f"{v30:,}")
                    
                    # Sponsorship Revenue Estimate
                    st.divider()
                    st.subheader("Sponsorship Revenue Estimate")
                    
                    metrics = ChannelMetrics(
                        subscribers=channel.subscribers,
                        total_views=channel.total_views,
                        video_count=channel.video_count,
                        average_views=channel.average_views,
                        monthly_views=monthly_views,
                        recent_videos=sponsor_videos
                    )
                    
                    result = estimate_sponsor_revenue(metrics, sponsor_videos)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Brand Deal Rate", format_currency(result.brand_deal_rate), help="Per integration")
                    c2.metric("Annual Uploads", result.annual_uploads, upload_frequency_label(result.annual_uploads))
                    c3.metric("Yearly Sponsor Revenue", format_currency(result.yearly_potential))
                    
                    st.info(f"Confidence: {result.confidence.upper()}")
                    
                    # Valuation estimate
                    if monthly_views and monthly_views > 0:
                        # Rough revenue estimate: $2-4 CPM on monthly views
                        est_monthly_rev = monthly_views * 0.003  # $3 CPM estimate
                        
                        st.divider()
                        st.subheader("Acquisition Valuation Estimate")
                        st.caption("Based on estimated monthly revenue from AdSense + sponsorships")
                        
                        monthly_sponsor = result.yearly_potential / 12
                        total_monthly = est_monthly_rev + monthly_sponsor
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Est. Monthly AdSense", f"${est_monthly_rev:,.0f}", help="Assumes ~$3 CPM")
                        c2.metric("Est. Monthly Sponsors", f"${monthly_sponsor:,.0f}")
                        c3.metric("Est. Total Monthly", f"${total_monthly:,.0f}")
                        
                        # Valuation at 24-36x
                        low_val = total_monthly * 24
                        high_val = total_monthly * 36
                        
                        c1, c2 = st.columns(2)
                        c1.metric("Valuation (24x)", f"${low_val:,.0f}")
                        c2.metric("Valuation (36x)", f"${high_val:,.0f}")
                    
                    with st.expander("Calculation Details"):
                        st.write("**Sponsor Revenue Formula:**")
                        st.code(f"Brand Rate = 0.0685 × ({channel.average_views:,})^0.961 = {format_currency(result.brand_deal_rate)}")
                        st.code(f"Yearly = {format_currency(result.brand_deal_rate)} × {result.annual_uploads} × 0.9 = {format_currency(result.yearly_potential)}")
                        st.write("**Notes:**")
                        for note in result.notes:
                            st.write(f"• {note}")
                    
                except Exception as e:
                    st.error(f"Error analyzing channel: {e}")
        
        elif analyze_btn and not channel_input:
            st.warning("Please enter a channel URL or handle")

    # === Manual Valuation ===
    with tab2:
        st.header("Manual Valuation Calculator")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            monthly_revenue = st.number_input("Monthly Revenue ($)", min_value=0.0, value=25000.0, step=500.0)
            monthly_views = st.number_input("Monthly Views", min_value=0.0, value=750000.0, step=10000.0)
        with col2:
            subscribers = st.number_input("Subscribers", min_value=0.0, value=250000.0, step=1000.0)
            age_years = st.number_input("Channel Age (years)", min_value=0.0, value=3.5, step=0.5)
        with col3:
            niche = st.selectbox("Niche", ["entertainment", "education", "finance", "tech", "lifestyle"])
        
        if st.button("Calculate Valuation", key="val_btn"):
            base_low, base_high, base_note = base_multiple_range(niche)
            adjustments = [base_note]
            adj_total = 0.0

            adj, note = engagement_adjustment(monthly_views, subscribers)
            adj_total += adj
            adjustments.append(note)

            adj, note = growth_proxy_adjustment(subscribers, age_years)
            adj_total += adj
            adjustments.append(note)

            low_mult = clamp(base_low + adj_total, 12.0, 60.0)
            high_mult = clamp(base_high + adj_total, 12.0, 60.0)
            if low_mult > high_mult:
                low_mult, high_mult = high_mult, low_mult

            low_val, mid_val, high_val = valuation_range(monthly_revenue, low_mult, high_mult)

            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Low", f"${low_val:,.0f}")
            c2.metric("Mid", f"${mid_val:,.0f}")
            c3.metric("High", f"${high_val:,.0f}")
            
            st.info(f"Multiple range: {low_mult:.1f}x - {high_mult:.1f}x")
            
            with st.expander("Details"):
                for item in adjustments:
                    st.write(f"• {item}")

    # === Manual Sponsor Revenue ===
    with tab3:
        st.header("Manual Sponsor Revenue Calculator")
        
        col1, col2 = st.columns(2)
        with col1:
            subs = st.number_input("Subscribers", min_value=0, value=250000, step=10000, key="sp_subs")
            avg_views = st.number_input("Avg Views/Video", min_value=0, value=100000, step=5000)
            video_count = st.number_input("Total Videos", min_value=0, value=150, step=10)
        with col2:
            total_views = st.number_input("Total Channel Views", min_value=0, value=50000000, step=1000000)
            sp_niche = st.selectbox("Niche", ["business", "education", "tech", "finance", "entertainment", "lifestyle", "gaming"], key="sp_niche")
            upload_freq = st.selectbox("Upload Frequency", ["Daily", "2-3x/week", "Weekly", "Biweekly", "Monthly", "< Monthly"])
        
        freq_map = {"Daily": 365, "2-3x/week": 130, "Weekly": 52, "Biweekly": 26, "Monthly": 12, "< Monthly": 6}
        
        if st.button("Calculate Revenue", key="rev_btn"):
            if avg_views <= 0:
                st.error("Average views must be > 0")
            else:
                metrics = ChannelMetrics(
                    subscribers=subs, total_views=total_views, video_count=video_count,
                    average_views=avg_views, monthly_views=None
                )
                result = estimate_sponsor_revenue(metrics)
                result.annual_uploads = freq_map.get(upload_freq, 52)
                result.yearly_potential = int(result.brand_deal_rate * result.annual_uploads * 0.9)

                st.divider()
                c1, c2, c3 = st.columns(3)
                c1.metric("Brand Deal Rate", format_currency(result.brand_deal_rate))
                c2.metric("Annual Uploads", result.annual_uploads)
                c3.metric("Yearly Potential", format_currency(result.yearly_potential))
                
                st.info(f"Confidence: {result.confidence.upper()}")
                
                # Rate table
                st.subheader("Rate Reference")
                data = []
                for v in [10000, 25000, 50000, 100000, 250000, 500000, 1000000]:
                    r = calculate_brand_deal_rate(v)
                    data.append({"Views": f"{v:,}", "Rate": format_currency(r), "CPM": f"${(r/v)*1000:.2f}"})
                st.table(data)

    # === Transcript Processor ===
    with tab4:
        st.header("Transcript Processor")
        
        upload = st.file_uploader("Upload transcript", type=["txt", "md"])
        
        if upload:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{upload.name}") as tmp:
                tmp.write(upload.read())
                temp_path = tmp.name

            result = process_transcript(temp_path)

            st.divider()
            st.subheader("Summary")
            st.write(result.get("summary", "No summary available."))
            
            st.subheader("Key Decisions")
            for d in (result.get("key_decisions") or []):
                st.write(f"• {d}")
            
            st.subheader("Action Items")
            for item in (result.get("action_items") or []):
                st.write(f"• **{item.get('task')}** — {item.get('assignee', 'Unassigned')}")


if __name__ == "__main__":
    main()
