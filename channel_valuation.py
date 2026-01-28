#!/usr/bin/env python3
import argparse
from typing import List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate a YouTube channel valuation range for acquisitions."
    )
    parser.add_argument("monthly_revenue", type=float, help="Monthly revenue in USD")
    parser.add_argument("monthly_views", type=float, help="Monthly views")
    parser.add_argument("subscribers", type=float, help="Subscriber count")
    parser.add_argument("age_years", type=float, help="Channel age in years")
    parser.add_argument(
        "niche",
        choices=["entertainment", "education", "finance", "tech", "lifestyle"],
        help="Channel niche",
    )
    return parser.parse_args()


def base_multiple_range(niche: str) -> Tuple[float, float, str]:
    if niche in {"finance", "education"}:
        return 30.0, 48.0, "Premium niche"
    return 24.0, 36.0, "Standard niche"


def engagement_adjustment(monthly_views: float, subscribers: float) -> Tuple[float, str]:
    if subscribers <= 0:
        return -2.0, "Very low engagement (no subscribers)"
    views_per_sub = monthly_views / subscribers
    if views_per_sub >= 1.5:
        return 2.0, f"High engagement ({views_per_sub:.2f} views/sub)"
    if views_per_sub < 0.5:
        return -2.0, f"Low engagement ({views_per_sub:.2f} views/sub)"
    return 0.0, f"Moderate engagement ({views_per_sub:.2f} views/sub)"


def growth_proxy_adjustment(subscribers: float, age_years: float) -> Tuple[float, str]:
    if age_years <= 0:
        return -2.0, "Unreliable age input"
    subs_per_year = subscribers / age_years
    if subs_per_year >= 100_000:
        return 2.0, f"Strong growth proxy ({subs_per_year:,.0f} subs/year)"
    if subs_per_year <= 20_000:
        return -2.0, f"Slow growth proxy ({subs_per_year:,.0f} subs/year)"
    return 0.0, f"Steady growth proxy ({subs_per_year:,.0f} subs/year)"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def valuation_range(monthly_revenue: float, low_mult: float, high_mult: float) -> Tuple[float, float, float]:
    low = monthly_revenue * low_mult
    high = monthly_revenue * high_mult
    mid = (low + high) / 2.0
    return low, mid, high


def main() -> None:
    args = parse_args()

    if args.monthly_revenue < 0 or args.monthly_views < 0 or args.subscribers < 0 or args.age_years < 0:
        raise SystemExit("All numeric inputs must be non-negative.")

    base_low, base_high, base_note = base_multiple_range(args.niche)

    adjustments: List[str] = [base_note]
    adj_total = 0.0

    adj, note = engagement_adjustment(args.monthly_views, args.subscribers)
    adj_total += adj
    adjustments.append(note)

    adj, note = growth_proxy_adjustment(args.subscribers, args.age_years)
    adj_total += adj
    adjustments.append(note)

    low_mult = clamp(base_low + adj_total, 12.0, 60.0)
    high_mult = clamp(base_high + adj_total, 12.0, 60.0)
    if low_mult > high_mult:
        low_mult, high_mult = high_mult, low_mult

    low_val, mid_val, high_val = valuation_range(args.monthly_revenue, low_mult, high_mult)

    print("Estimated valuation range (USD):")
    print(f"  Low:  ${low_val:,.0f}")
    print(f"  Mid:  ${mid_val:,.0f}")
    print(f"  High: ${high_val:,.0f}")
    print()
    print("Revenue multiple used (monthly revenue):")
    print(f"  Low/Mid/High: {low_mult:.1f}x / {(low_mult + high_mult) / 2:.1f}x / {high_mult:.1f}x")
    print()
    print("Key factors affecting valuation:")
    for item in adjustments:
        print(f"  - {item}")


if __name__ == "__main__":
    main()
