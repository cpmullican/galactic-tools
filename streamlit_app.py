#!/usr/bin/env python3
"""
Galactic Media Group - YouTube Channel Acquisition Suite
Premium UI inspired by galactic.tv
"""
import tempfile
from typing import List

import streamlit as st

from channel_valuation import (
    base_multiple_range,
    clamp,
    engagement_adjustment,
    growth_proxy_adjustment,
    valuation_range,
)
from transcript_processor import process_transcript
from sponsor_revenue import (
    ChannelMetrics,
    estimate_sponsor_revenue,
    format_currency,
    upload_frequency_label,
    calculate_brand_deal_rate,
)


def _format_currency(value: float) -> str:
    return f"${value:,.0f}"


def _inject_styles() -> None:
    """Inject custom CSS matching Galactic website design."""
    st.markdown(
        """
        <style>
            :root {
                --bg-primary: #000000;
                --bg-secondary: #0D0C14;
                --bg-card: #0D0C14;
                --border-subtle: rgba(255, 255, 255, 0.1);
                --border-accent: rgba(99, 102, 241, 0.3);
                --text-primary: #ffffff;
                --text-secondary: #9ca3af;
                --text-muted: #6b7280;
                --accent-indigo: #6366f1;
                --accent-purple: #a855f7;
                --accent-emerald: #10b981;
                --gradient-primary: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
                --gradient-success: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
            }
            
            .stApp {
                background: #000000;
            }
            
            .stApp > header {
                background: transparent !important;
            }
            
            /* Sidebar */
            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0D0C14 0%, #000000 100%);
                border-right: 1px solid var(--border-subtle);
            }
            
            section[data-testid="stSidebar"] .stMarkdown {
                color: var(--text-primary);
            }
            
            /* Typography - system fonts for speed */
            h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
                font-weight: 600;
                color: var(--text-primary) !important;
            }
            
            p, span, label, .stMarkdown {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
                color: var(--text-secondary);
            }
            
            /* Hero Section */
            .hero-container {
                background: var(--bg-card);
                border: 1px solid var(--border-subtle);
                border-radius: 24px;
                padding: 2.5rem;
                margin-bottom: 2rem;
            }
            
            .hero-badge {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 1rem;
                background: rgba(99, 102, 241, 0.1);
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 999px;
                font-size: 0.75rem;
                font-weight: 600;
                color: #818cf8;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 1.5rem;
            }
            
            .hero-title {
                font-family: 'Outfit', sans-serif;
                font-size: 2.5rem;
                font-weight: 700;
                line-height: 1.2;
                margin-bottom: 1rem;
                background: linear-gradient(135deg, #ffffff 0%, rgba(255,255,255,0.7) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .hero-subtitle {
                font-size: 1.1rem;
                color: var(--text-secondary);
                max-width: 600px;
            }
            
            /* Glass Cards */
            .glass-card {
                background: var(--bg-card);
                border: 1px solid var(--border-subtle);
                border-radius: 16px;
                padding: 1.5rem;
            }
            
            /* Metric Cards */
            .metric-card {
                background: rgba(99, 102, 241, 0.08);
                border: 1px solid var(--border-subtle);
                border-radius: 16px;
                padding: 1.5rem;
                text-align: center;
            }
            
            .metric-label {
                font-size: 0.85rem;
                color: var(--text-muted);
                margin-bottom: 0.5rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            
            .metric-value {
                font-family: 'Outfit', sans-serif;
                font-size: 2rem;
                font-weight: 700;
                background: var(--gradient-primary);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .metric-value.success {
                background: var(--gradient-success);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .metric-delta {
                font-size: 0.85rem;
                color: var(--text-secondary);
                margin-top: 0.25rem;
            }
            
            /* Streamlit Metric Override */
            [data-testid="stMetric"] {
                background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(168, 85, 247, 0.04) 100%);
                border: 1px solid var(--border-subtle);
                border-radius: 16px;
                padding: 1.25rem !important;
            }
            
            [data-testid="stMetricLabel"] {
                color: var(--text-muted) !important;
            }
            
            [data-testid="stMetricValue"] {
                font-family: 'Outfit', sans-serif !important;
                font-weight: 700 !important;
                color: var(--text-primary) !important;
            }
            
            /* Buttons */
            .stButton > button {
                background: var(--gradient-primary) !important;
                color: white !important;
                border: none !important;
                border-radius: 12px !important;
                padding: 0.75rem 2rem !important;
                font-weight: 600 !important;
            }
            
            /* Form Elements */
            .stTextInput > div > div > input,
            .stNumberInput > div > div > input,
            .stSelectbox > div > div {
                background: #0D0C14 !important;
                border: 1px solid var(--border-subtle) !important;
                border-radius: 12px !important;
                color: var(--text-primary) !important;
            }
            
            /* Pills/Tags */
            .pill {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 1rem;
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 999px;
                font-size: 0.875rem;
                font-weight: 600;
                color: #34d399;
            }
            
            .pill.warning {
                background: rgba(245, 158, 11, 0.1);
                border-color: rgba(245, 158, 11, 0.3);
                color: #fbbf24;
            }
            
            .pill.info {
                background: rgba(99, 102, 241, 0.1);
                border-color: rgba(99, 102, 241, 0.3);
                color: #818cf8;
            }
            
            /* Tables */
            .stTable {
                background: var(--bg-card) !important;
                border-radius: 16px !important;
                overflow: hidden;
            }
            
            thead tr th {
                background: rgba(99, 102, 241, 0.1) !important;
                color: var(--text-primary) !important;
                font-family: 'Inter', sans-serif !important;
                font-weight: 600 !important;
                border: none !important;
            }
            
            tbody tr td {
                background: transparent !important;
                color: var(--text-secondary) !important;
                border-bottom: 1px solid var(--border-subtle) !important;
            }
            
            /* Expanders */
            .streamlit-expanderHeader {
                background: var(--bg-card) !important;
                border: 1px solid var(--border-subtle) !important;
                border-radius: 12px !important;
                color: var(--text-primary) !important;
            }
            
            .streamlit-expanderContent {
                background: var(--bg-secondary) !important;
                border: 1px solid var(--border-subtle) !important;
                border-top: none !important;
                border-radius: 0 0 12px 12px !important;
            }
            
            /* Info/Warning boxes */
            .stAlert {
                background: var(--bg-card) !important;
                border: 1px solid var(--border-subtle) !important;
                border-radius: 12px !important;
                color: var(--text-secondary) !important;
            }
            
            /* Dividers */
            hr {
                border-color: var(--border-subtle) !important;
                margin: 2rem 0 !important;
            }
            
            /* Section Headers */
            .section-header {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-bottom: 1.5rem;
            }
            
            .section-icon {
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: rgba(99, 102, 241, 0.1);
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 12px;
                font-size: 1.25rem;
            }
            
            .section-title {
                font-family: 'Outfit', sans-serif;
                font-size: 1.5rem;
                font-weight: 600;
                color: var(--text-primary);
            }
            
            /* Stats Grid */
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 1rem;
                margin: 1.5rem 0;
            }
            
            /* Confidence Badge */
            .confidence-badge {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 1rem;
                border-radius: 999px;
                font-size: 0.85rem;
                font-weight: 600;
            }
            
            .confidence-high {
                background: rgba(16, 185, 129, 0.15);
                border: 1px solid rgba(16, 185, 129, 0.4);
                color: #34d399;
            }
            
            .confidence-medium {
                background: rgba(245, 158, 11, 0.15);
                border: 1px solid rgba(245, 158, 11, 0.4);
                color: #fbbf24;
            }
            
            .confidence-low {
                background: rgba(239, 68, 68, 0.15);
                border: 1px solid rgba(239, 68, 68, 0.4);
                color: #f87171;
            }
            
            /* Hide Streamlit branding but keep menu functional */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            
            /* Keep header for mobile menu toggle */
            header[data-testid="stHeader"] {
                background: transparent !important;
                backdrop-filter: none !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    st.markdown(
        """
        <div class="hero-container">
            <div class="hero-badge">
                🚀 Galactic Media Group
            </div>
            <h1 class="hero-title">YouTube Channel Acquisition Suite</h1>
            <p class="hero-subtitle">
                Professional-grade tools for channel valuation, sponsorship revenue estimation, 
                and deal analysis. Built for operators who acquire and scale YouTube channels.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_valuation() -> None:
    st.markdown(
        """
        <div class="section-header">
            <div class="section-icon">💰</div>
            <span class="section-title">Channel Valuation Calculator</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Estimate acquisition value based on revenue multiples, engagement, and growth signals.")

    with st.form("valuation_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            monthly_revenue = st.number_input(
                "Monthly Revenue (USD)", min_value=0.0, step=500.0, value=25000.0,
                help="Average monthly revenue from all sources"
            )
            monthly_views = st.number_input(
                "Monthly Views", min_value=0.0, step=10000.0, value=750000.0,
                help="Average monthly video views"
            )
        with col2:
            subscribers = st.number_input(
                "Subscribers", min_value=0.0, step=1000.0, value=250000.0,
                help="Current subscriber count"
            )
            age_years = st.number_input(
                "Channel Age (years)", min_value=0.0, step=0.5, value=3.5,
                help="Years since channel creation"
            )
        with col3:
            niche = st.selectbox(
                "Content Niche",
                ["entertainment", "education", "finance", "tech", "lifestyle"],
                help="Primary content category"
            )
        submitted = st.form_submit_button("Calculate Valuation")

    if not submitted:
        st.info("💡 Enter channel metrics above and click Calculate to see valuation range.")
        return

    if any(v < 0 for v in [monthly_revenue, monthly_views, subscribers, age_years]):
        st.error("All numeric inputs must be non-negative.")
        return

    base_low, base_high, base_note = base_multiple_range(niche)
    adjustments: List[str] = [base_note]
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

    st.markdown("---")
    
    # Results in custom metric cards
    st.markdown(
        f"""
        <div class="stats-grid">
            <div class="metric-card">
                <div class="metric-label">Low Estimate</div>
                <div class="metric-value">{_format_currency(low_val)}</div>
                <div class="metric-delta">{low_mult:.1f}x monthly revenue</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Mid Estimate</div>
                <div class="metric-value success">{_format_currency(mid_val)}</div>
                <div class="metric-delta">Target valuation</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">High Estimate</div>
                <div class="metric-value">{_format_currency(high_val)}</div>
                <div class="metric-delta">{high_mult:.1f}x monthly revenue</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="pill info">Revenue Multiple Range: {low_mult:.1f}x – {high_mult:.1f}x</div>',
        unsafe_allow_html=True,
    )

    with st.expander("📊 Valuation Methodology"):
        st.markdown("**Adjustments Applied:**")
        for item in adjustments:
            st.markdown(f"- {item}")
        st.markdown("---")
        st.caption(
            "Multiples derived from engagement ratio (views/subscriber) and growth proxy (subscribers/year). "
            "Niche affects base multiple range. Finance and education command premium valuations."
        )


def _render_transcript_processor() -> None:
    st.markdown(
        """
        <div class="section-header">
            <div class="section-icon">📝</div>
            <span class="section-title">Transcript Processor</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Extract action items, decisions, and summaries from meeting transcripts.")

    upload = st.file_uploader("Upload transcript (.txt or .md)", type=["txt", "md"])
    if not upload:
        st.info("📤 Upload a meeting transcript to begin analysis.")
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{upload.name}") as tmp:
        tmp.write(upload.read())
        temp_path = tmp.name

    result = process_transcript(temp_path)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📅 Meeting Date**")
        st.write(result.get("meeting_date") or "Not detected")
    with col2:
        st.markdown("**👥 Participants**")
        participants = result.get("participants") or []
        if participants:
            st.write(", ".join(participants))
        else:
            st.write("Not detected")

    st.markdown("**📋 Executive Summary**")
    st.success(result.get("summary", "No summary available."))

    st.markdown("**✅ Key Decisions**")
    decisions = result.get("key_decisions") or []
    if decisions:
        for decision in decisions:
            st.markdown(f"- {decision}")
    else:
        st.write("No explicit decisions detected.")

    st.markdown("**🎯 Action Items**")
    action_items = result.get("action_items") or []
    if action_items:
        for item in action_items:
            assignee = item.get("assignee") or "Unassigned"
            due = item.get("due_date") or "No due date"
            st.markdown(
                f"- **{item.get('task','')}**  \n  Owner: {assignee} · Due: {due}"
            )
    else:
        st.write("No explicit action items detected.")


def _render_sponsor_revenue() -> None:
    st.markdown(
        """
        <div class="section-header">
            <div class="section-icon">💎</div>
            <span class="section-title">Sponsorship Revenue Estimator</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Project brand deal revenue potential using Galactic's proprietary algorithm.")
    
    st.markdown(
        """
        <div class="glass-card" style="margin-bottom: 1.5rem;">
            <strong style="color: #818cf8;">💡 How it works</strong>
            <p style="margin-top: 0.5rem; margin-bottom: 0;">
                This calculator uses the same algorithm powering Galactic's creator evaluation tool. 
                It estimates brand deal rates based on average views and upload frequency to project 
                yearly sponsorship revenue potential.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("sponsor_form"):
        col1, col2 = st.columns(2)
        with col1:
            subscribers = st.number_input(
                "Subscribers", min_value=0, step=10000, value=250000,
                help="Total subscriber count"
            )
            average_views = st.number_input(
                "Average Views per Video", min_value=0, step=5000, value=100000,
                help="Typical views on a standard video (not shorts)"
            )
            monthly_views = st.number_input(
                "Monthly Views (optional)", min_value=0, step=100000, value=0,
                help="Total monthly views from YouTube Analytics"
            )
        with col2:
            total_views = st.number_input(
                "Total Channel Views", min_value=0, step=1000000, value=50000000,
                help="Lifetime total views"
            )
            video_count = st.number_input(
                "Total Video Count", min_value=0, step=10, value=150,
                help="Number of videos on channel"
            )
            niche = st.selectbox(
                "Content Niche",
                ["business", "education", "tech", "finance", "entertainment", "lifestyle", "gaming"],
                help="Primary content category (affects rate benchmarks)"
            )
        
        st.markdown("---")
        st.markdown("**⚙️ Upload Frequency Override**")
        use_custom_frequency = st.checkbox("Set custom upload frequency")
        
        if use_custom_frequency:
            upload_frequency = st.selectbox(
                "Upload Frequency",
                ["Daily", "2-3x per week", "Weekly", "Biweekly", "Monthly", "Less than monthly"],
            )
            frequency_map = {
                "Daily": 365, "2-3x per week": 130, "Weekly": 52,
                "Biweekly": 26, "Monthly": 12, "Less than monthly": 6
            }
            custom_annual_uploads = frequency_map.get(upload_frequency, 52)
        else:
            custom_annual_uploads = None
        
        submitted = st.form_submit_button("Calculate Revenue Potential")

    if not submitted:
        st.info("💡 Enter channel metrics to estimate sponsorship revenue potential.")
        return

    if average_views <= 0:
        st.error("Average views must be greater than 0.")
        return

    metrics = ChannelMetrics(
        subscribers=subscribers, total_views=total_views, video_count=video_count,
        average_views=average_views, monthly_views=monthly_views if monthly_views > 0 else None
    )

    result = estimate_sponsor_revenue(metrics)
    
    if custom_annual_uploads:
        result.annual_uploads = custom_annual_uploads
        result.yearly_potential = int(result.brand_deal_rate * custom_annual_uploads * 0.9)
        result.notes.append(f"Using custom upload frequency: {upload_frequency}")

    st.markdown("---")
    
    # Results
    st.markdown(
        f"""
        <div class="stats-grid">
            <div class="metric-card">
                <div class="metric-label">Brand Deal Rate</div>
                <div class="metric-value">{format_currency(result.brand_deal_rate)}</div>
                <div class="metric-delta">Per integration</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Annual Uploads</div>
                <div class="metric-value">{result.annual_uploads}</div>
                <div class="metric-delta">{upload_frequency_label(result.annual_uploads)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Yearly Potential</div>
                <div class="metric-value success">{format_currency(result.yearly_potential)}</div>
                <div class="metric-delta">Sponsorship revenue</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Confidence badge
    conf_class = f"confidence-{result.confidence}"
    st.markdown(
        f'<div class="confidence-badge {conf_class}">Confidence: {result.confidence.upper()}</div>',
        unsafe_allow_html=True,
    )

    # Rate breakdown
    st.markdown("---")
    st.markdown("### 📊 Rate Breakdown")
    
    effective_cpm = (result.brand_deal_rate / average_views) * 1000 if average_views > 0 else 0
    
    breakdown_cols = st.columns(4)
    breakdown_cols[0].metric("Avg Views", f"{average_views:,}")
    breakdown_cols[1].metric("Formula", "0.0685 × v^0.961")
    breakdown_cols[2].metric("Per Integration", format_currency(result.brand_deal_rate))
    breakdown_cols[3].metric("Effective CPM", f"${effective_cpm:.2f}")

    # Quick reference table
    st.markdown("---")
    st.markdown("### 📈 Rate Reference Table")
    
    view_benchmarks = [10000, 25000, 50000, 100000, 250000, 500000, 1000000]
    rate_data = []
    for views in view_benchmarks:
        rate = calculate_brand_deal_rate(views)
        rate_data.append({
            "Avg Views": f"{views:,}",
            "Est. Rate": format_currency(rate),
            "Effective CPM": f"${(rate/views)*1000:.2f}"
        })
    
    st.table(rate_data)

    with st.expander("📋 Calculation Notes"):
        st.markdown("**Factors considered:**")
        for note in result.notes:
            st.markdown(f"- {note}")
        st.markdown("---")
        st.markdown(
            """
            **Methodology:**
            - Brand deal rate: `rate = 0.0685 × (avg_views)^0.961`
            - Yearly potential: `rate × annual_uploads × 0.9` (assumes 90% integration rate)
            - Formula derived from market data in business/education niche
            """
        )
    
    st.info(
        f"💡 **Niche note:** {niche.title()} content. Business, finance, and education niches "
        "typically command 20-50% higher rates due to higher-value audiences."
    )


def main() -> None:
    st.set_page_config(
        page_title="Galactic Media Group | Acquisition Tools",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _inject_styles()

    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 1rem 0;">
                <div style="font-size: 1.5rem; font-weight: 700; color: white; font-family: 'Outfit', sans-serif;">
                    🚀 Galactic
                </div>
                <div style="font-size: 0.85rem; color: #6b7280; margin-top: 0.25rem;">
                    Acquisition Toolkit
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("---")
        page = st.radio(
            "Navigate",
            ["💰 Channel Valuation", "💎 Sponsor Revenue", "📝 Transcript Processor"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.markdown(
            """
            <div style="font-size: 0.8rem; color: #6b7280;">
                <strong style="color: #9ca3af;">Tools</strong><br>
                • Channel valuation<br>
                • Sponsor revenue estimator<br>
                • Transcript processor<br><br>
                <strong style="color: #9ca3af;">Coming Soon</strong><br>
                • Channel lookup API<br>
                • Deal flow tracker
            </div>
            """,
            unsafe_allow_html=True,
        )

    _render_header()

    if "Valuation" in page:
        _render_valuation()
    elif "Sponsor" in page:
        _render_sponsor_revenue()
    else:
        _render_transcript_processor()


if __name__ == "__main__":
    main()
