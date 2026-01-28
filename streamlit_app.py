#!/usr/bin/env python3
"""Galactic Media Group - YouTube Channel Acquisition Tools"""
import tempfile
from typing import List
import streamlit as st

from channel_valuation import (
    base_multiple_range, clamp, engagement_adjustment,
    growth_proxy_adjustment, valuation_range,
)
from transcript_processor import process_transcript
from sponsor_revenue import (
    ChannelMetrics, estimate_sponsor_revenue, format_currency,
    upload_frequency_label, calculate_brand_deal_rate,
)


def main():
    st.set_page_config(
        page_title="Galactic Tools",
        page_icon="🚀",
        layout="wide",
    )

    st.title("🚀 Galactic Acquisition Tools")
    
    tab1, tab2, tab3 = st.tabs(["Channel Valuation", "Sponsor Revenue", "Transcript Processor"])
    
    # === Channel Valuation ===
    with tab1:
        st.header("Channel Valuation Calculator")
        
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

    # === Sponsor Revenue ===
    with tab2:
        st.header("Sponsorship Revenue Estimator")
        
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
    with tab3:
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
