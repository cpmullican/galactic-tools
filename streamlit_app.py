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
            ["Channel Valuation", "Transcript Processor"],
            label_visibility="visible",
        )
        st.markdown("---")
        st.markdown("**Tools included**")
        st.markdown("- Channel valuation calculator")
        st.markdown("- Transcript processor")
        st.markdown("---")
        st.markdown("Need channel lookup? Coming soon.")

    _render_header()

    if page == "Channel Valuation":
        _render_valuation()
    else:
        _render_transcript_processor()


if __name__ == "__main__":
    main()
