#!/usr/bin/env python3
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


def _render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-badge">Galactic Media Group</div>
            <h1>YouTube Channel Acquisition Suite</h1>
            <p>Evaluate channels and extract actionable insights in minutes.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_valuation() -> None:
    st.subheader("Channel Valuation Calculator")
    st.caption("Estimate a valuation range based on revenue, engagement, and growth signals.")

    with st.form("valuation_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            monthly_revenue = st.number_input(
                "Monthly revenue (USD)", min_value=0.0, step=500.0, value=25000.0
            )
            monthly_views = st.number_input(
                "Monthly views", min_value=0.0, step=10000.0, value=750000.0
            )
        with col2:
            subscribers = st.number_input(
                "Subscribers", min_value=0.0, step=1000.0, value=250000.0
            )
            age_years = st.number_input(
                "Channel age (years)", min_value=0.0, step=0.5, value=3.5
            )
        with col3:
            niche = st.selectbox(
                "Channel niche",
                ["entertainment", "education", "finance", "tech", "lifestyle"],
            )
        submitted = st.form_submit_button("Calculate valuation")

    if not submitted:
        st.info("Enter channel metrics and calculate to view a valuation range.")
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
    metric_cols = st.columns(3)
    metric_cols[0].metric("Low valuation", _format_currency(low_val))
    metric_cols[1].metric("Mid valuation", _format_currency(mid_val))
    metric_cols[2].metric("High valuation", _format_currency(high_val))

    st.markdown(
        f"<div class='pill'>Revenue multiple: {low_mult:.1f}x to {high_mult:.1f}x</div>",
        unsafe_allow_html=True,
    )

    with st.expander("Why this valuation?"):
        st.markdown("**Key drivers applied**")
        for item in adjustments:
            st.markdown(f"- {item}")
        st.caption(
            "Adjustments are derived from engagement (views per subscriber) and growth proxy (subs per year)."
        )


def _render_transcript_processor() -> None:
    st.subheader("Transcript Processor")
    st.caption("Upload a meeting transcript to extract action items, decisions, and a summary.")

    upload = st.file_uploader("Upload transcript (.txt or .md)", type=["txt", "md"])
    if not upload:
        st.info("Upload a transcript to begin analysis.")
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{upload.name}") as tmp:
        tmp.write(upload.read())
        temp_path = tmp.name

    result = process_transcript(temp_path)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Meeting date**")
        st.write(result.get("meeting_date") or "Not detected")
    with col2:
        st.markdown("**Participants**")
        participants = result.get("participants") or []
        if participants:
            st.write(", ".join(participants))
        else:
            st.write("Not detected")

    st.markdown("**Executive summary**")
    st.success(result.get("summary", "No summary available."))

    st.markdown("**Key decisions**")
    decisions = result.get("key_decisions") or []
    if decisions:
        for decision in decisions:
            st.markdown(f"- {decision}")
    else:
        st.write("No explicit decisions detected.")

    st.markdown("**Action items**")
    action_items = result.get("action_items") or []
    if action_items:
        for item in action_items:
            assignee = item.get("assignee") or "Unassigned"
            due = item.get("due_date") or "No due date"
            st.markdown(
                f"- **Task:** {item.get('task','')}  \\n  **Owner:** {assignee} · **Due:** {due}"
            )
    else:
        st.write("No explicit action items detected.")


def _render_sponsor_revenue() -> None:
    st.subheader("Sponsorship Revenue Estimator")
    st.caption("Estimate potential brand deal revenue based on channel metrics.")
    
    st.markdown(
        """
        <div style="background: rgba(82, 209, 255, 0.1); border: 1px solid rgba(82, 209, 255, 0.3); 
                    border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem;">
            <strong>💡 How it works:</strong> This calculator uses the same algorithm powering 
            Galactic's creator evaluation tool. It estimates brand deal rates based on average 
            views and upload frequency to project yearly sponsorship revenue.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("sponsor_form"):
        col1, col2 = st.columns(2)
        with col1:
            subscribers = st.number_input(
                "Subscribers",
                min_value=0,
                step=10000,
                value=250000,
                help="Total subscriber count"
            )
            average_views = st.number_input(
                "Average views per video",
                min_value=0,
                step=5000,
                value=100000,
                help="Typical views on a standard video (not shorts)"
            )
            monthly_views = st.number_input(
                "Monthly views (optional)",
                min_value=0,
                step=100000,
                value=0,
                help="Total monthly views from YouTube Analytics"
            )
        with col2:
            total_views = st.number_input(
                "Total channel views",
                min_value=0,
                step=1000000,
                value=50000000,
                help="Lifetime total views"
            )
            video_count = st.number_input(
                "Total video count",
                min_value=0,
                step=10,
                value=150,
                help="Number of videos on channel"
            )
            niche = st.selectbox(
                "Content niche",
                ["business", "education", "tech", "finance", "entertainment", "lifestyle", "gaming"],
                help="Primary content category (affects rate benchmarks)"
            )
        
        st.markdown("---")
        st.markdown("**Upload Frequency Override (Optional)**")
        use_custom_frequency = st.checkbox("Set custom upload frequency")
        
        if use_custom_frequency:
            upload_frequency = st.selectbox(
                "Upload frequency",
                ["Daily", "2-3x per week", "Weekly", "Biweekly", "Monthly", "Less than monthly"],
            )
            frequency_map = {
                "Daily": 365,
                "2-3x per week": 130,
                "Weekly": 52,
                "Biweekly": 26,
                "Monthly": 12,
                "Less than monthly": 6
            }
            custom_annual_uploads = frequency_map.get(upload_frequency, 52)
        else:
            custom_annual_uploads = None
        
        submitted = st.form_submit_button("Calculate Revenue Potential")

    if not submitted:
        st.info("Enter channel metrics to estimate sponsorship revenue potential.")
        return

    if average_views <= 0:
        st.error("Average views must be greater than 0.")
        return

    # Build metrics object
    metrics = ChannelMetrics(
        subscribers=subscribers,
        total_views=total_views,
        video_count=video_count,
        average_views=average_views,
        monthly_views=monthly_views if monthly_views > 0 else None
    )

    # Get estimate
    result = estimate_sponsor_revenue(metrics)
    
    # Override upload frequency if custom
    if custom_annual_uploads:
        result.annual_uploads = custom_annual_uploads
        result.yearly_potential = int(result.brand_deal_rate * custom_annual_uploads * 0.9)
        result.notes.append(f"Using custom upload frequency: {upload_frequency}")

    st.markdown("---")
    
    # Main metrics
    metric_cols = st.columns(3)
    metric_cols[0].metric(
        "Brand Deal Rate",
        format_currency(result.brand_deal_rate),
        help="Estimated rate per sponsored integration"
    )
    metric_cols[1].metric(
        "Annual Uploads",
        f"{result.annual_uploads}",
        f"({upload_frequency_label(result.annual_uploads)})",
        help="Estimated videos per year"
    )
    metric_cols[2].metric(
        "Yearly Revenue Potential",
        format_currency(result.yearly_potential),
        help="Estimated annual sponsorship revenue"
    )

    # Confidence indicator
    confidence_colors = {
        "high": ("rgba(123, 242, 155, 0.2)", "rgba(123, 242, 155, 0.5)", "#7bf29b"),
        "medium": ("rgba(255, 193, 7, 0.2)", "rgba(255, 193, 7, 0.5)", "#ffc107"),
        "low": ("rgba(255, 107, 107, 0.2)", "rgba(255, 107, 107, 0.5)", "#ff6b6b"),
    }
    bg, border, text = confidence_colors.get(result.confidence, confidence_colors["medium"])
    
    st.markdown(
        f"""
        <div style="margin-top: 1rem; display: inline-block; padding: 0.4rem 1rem; 
                    border-radius: 999px; background: {bg}; border: 1px solid {border}; 
                    color: {text}; font-weight: 600; font-size: 0.85rem;">
            Confidence: {result.confidence.upper()}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Rate breakdown
    st.markdown("---")
    st.markdown("### Rate Breakdown")
    
    breakdown_cols = st.columns(4)
    breakdown_cols[0].markdown("**Views**")
    breakdown_cols[0].markdown(f"{average_views:,}")
    
    breakdown_cols[1].markdown("**Formula**")
    breakdown_cols[1].markdown("0.0685 × views^0.961")
    
    breakdown_cols[2].markdown("**Per Integration**")
    breakdown_cols[2].markdown(f"**{format_currency(result.brand_deal_rate)}**")
    
    breakdown_cols[3].markdown("**Comparable CPM**")
    if average_views > 0:
        effective_cpm = (result.brand_deal_rate / average_views) * 1000
        breakdown_cols[3].markdown(f"${effective_cpm:.2f}")
    else:
        breakdown_cols[3].markdown("N/A")

    # Quick rate table
    st.markdown("---")
    st.markdown("### Quick Reference: Brand Deal Rates by Views")
    
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

    # Notes
    with st.expander("Calculation Notes"):
        st.markdown("**Factors considered:**")
        for note in result.notes:
            st.markdown(f"- {note}")
        
        st.markdown("---")
        st.markdown(
            """
            **Methodology:**
            - Brand deal rate formula: `rate = 0.0685 × (avg_views)^0.961`
            - Yearly potential: `rate × annual_uploads × 0.9` (assumes 90% integration rate)
            - Formula derived from market data in business/education niche
            - Actual rates vary by niche, audience demographics, and negotiation
            """
        )
    
    # Niche adjustment note
    st.info(
        f"💡 **Niche note:** You selected '{niche}'. Business, finance, and education niches "
        "typically command 20-50% higher rates than entertainment/lifestyle due to higher-value audiences."
    )


def main() -> None:
    st.set_page_config(
        page_title="Galactic Media Group | YouTube Acquisition Tools",
        page_icon="🚀",
        layout="wide",
    )

    st.markdown(
        """
        <style>
            :root {
                --galactic-bg: #0b0f1a;
                --galactic-card: #131a2a;
                --galactic-accent: #52d1ff;
                --galactic-accent-2: #7bf29b;
                --galactic-text: #e7ecf6;
                --galactic-muted: #9aa7c2;
            }
            .stApp {
                background: radial-gradient(circle at top, #10172b 0%, #0b0f1a 55%, #05070f 100%);
                color: var(--galactic-text);
            }
            section[data-testid="stSidebar"] {
                background: #0c1324;
                border-right: 1px solid #1b2741;
            }
            .hero {
                background: linear-gradient(120deg, rgba(82, 209, 255, 0.15), rgba(123, 242, 155, 0.08));
                border: 1px solid rgba(82, 209, 255, 0.2);
                padding: 1.5rem 2rem;
                border-radius: 18px;
                margin-bottom: 1.5rem;
            }
            .hero h1 {
                font-size: 2.2rem;
                margin-bottom: 0.4rem;
            }
            .hero-badge {
                display: inline-block;
                padding: 0.2rem 0.7rem;
                border-radius: 999px;
                background: rgba(82, 209, 255, 0.2);
                color: var(--galactic-accent);
                font-weight: 600;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                font-size: 0.7rem;
                margin-bottom: 0.8rem;
            }
            .pill {
                margin-top: 0.8rem;
                display: inline-block;
                padding: 0.35rem 0.85rem;
                border-radius: 999px;
                background: rgba(123, 242, 155, 0.12);
                border: 1px solid rgba(123, 242, 155, 0.35);
                color: var(--galactic-accent-2);
                font-weight: 600;
            }
            .stMetric {
                background: var(--galactic-card);
                border-radius: 14px;
                padding: 1rem;
                border: 1px solid rgba(154, 167, 194, 0.15);
            }
            .stMetric label {
                color: var(--galactic-muted) !important;
            }
            .stButton > button {
                background: linear-gradient(120deg, #52d1ff, #7bf29b);
                color: #05121d;
                border: none;
                font-weight: 700;
                padding: 0.6rem 1.2rem;
            }
            .stTextInput > div > div input,
            .stNumberInput input,
            .stSelectbox select {
                background: #10182c;
                color: var(--galactic-text);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("## Galactic Media Group")
        st.caption("Acquisition diligence toolkit")
        page = st.radio(
            "Navigate",
            ["Channel Valuation", "Sponsor Revenue", "Transcript Processor"],
            label_visibility="visible",
        )
        st.markdown("---")
        st.markdown("**Tools included**")
        st.markdown("- Channel valuation calculator")
        st.markdown("- Sponsor revenue estimator")
        st.markdown("- Transcript processor")
        st.markdown("---")
        st.markdown("Need channel lookup? Coming soon.")

    _render_header()

    if page == "Channel Valuation":
        _render_valuation()
    elif page == "Sponsor Revenue":
        _render_sponsor_revenue()
    else:
        _render_transcript_processor()


if __name__ == "__main__":
    main()
