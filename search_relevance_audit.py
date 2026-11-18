"""
E-Commerce Search Relevance & Zero-Result Query Auditor
Evaluates search-to-cart funnel conversion, flags high-volume null searches,
and maps spelling/synonym mismatches against active catalog keywords.
"""

from difflib import get_close_matches
import numpy as np
import pandas as pd


ACTIVE_CATALOG_TERMS = [
    "wireless earbuds",
    "running shoes",
    "iphone 16 case",
    "usb c fast charger",
    "laptop stand",
    "whey protein powder",
    "ergonomic office chair",
    "stainless steel water bottle",
    "mechanical keyboard",
    "yoga mat",
]


def simulate_search_logs(n_searches: int = 35000) -> pd.DataFrame:
    """Generates realistic onsite search logs including typos and low-CTR terms."""
    rng = np.random.default_rng(42)

    query_pool = [
        # Healthy high-intent terms
        ("wireless earbuds", 0.16, 45, 0.42, 0.14),
        ("running shoes", 0.14, 120, 0.38, 0.11),
        ("usb c fast charger", 0.11, 30, 0.46, 0.18),
        ("stainless steel water bottle", 0.09, 25, 0.35, 0.12),
        ("yoga mat", 0.08, 40, 0.40, 0.15),
        # Ranking issue (results exist, but relevant items buried low -> poor CTR)
        ("ergonomic office chair", 0.10, 65, 0.14, 0.03),
        ("mechanical keyboard", 0.08, 50, 0.16, 0.04),
        # Typo / Synonym gaps (triggers 0 results in strict keyword search)
        ("wireles earpods", 0.07, 0, 0.00, 0.00),
        ("runing shos", 0.06, 0, 0.00, 0.00),
        ("iphone 16 cover", 0.06, 0, 0.00, 0.00),
        ("protien powdr", 0.05, 0, 0.00, 0.00),
    ]

    queries = [q[0] for q in query_pool]
    weights = [q[1] for q in query_pool]

    chosen_idx = rng.choice(len(query_pool), size=n_searches, p=weights)

    records = []
    for i, idx in enumerate(chosen_idx):
        q_text, _, base_results, ctr_prob, atc_prob = query_pool[idx]
        results_count = base_results if base_results == 0 else int(max(1, rng.normal(base_results, 5)))
        clicked = 1 if (results_count > 0 and rng.random() < ctr_prob) else 0
        clicked_rank = int(rng.integers(1, 4)) if (clicked and ctr_prob > 0.25) else (int(rng.integers(6, 15)) if clicked else np.nan)
        added_to_cart = 1 if (clicked == 1 and rng.random() < (atc_prob / max(ctr_prob, 0.01))) else 0

        records.append({
            "search_id": f"SRC-{800000 + i}",
            "query": q_text,
            "results_count": results_count,
            "clicked": clicked,
            "clicked_rank": clicked_rank,
            "added_to_cart": added_to_cart
        })

    return pd.DataFrame(records)


def run_search_audit(df: pd.DataFrame):
    total_searches = len(df)
    non_zero = (df["results_count"] > 0).sum()
    zero_res = total_searches - non_zero
    clicks = df["clicked"].sum()
    carts = df["added_to_cart"].sum()

    print("\n--- Onsite Search Funnel Performance (Last 30 Days) ---")
    print(f"Total Searches        : {total_searches:,} (100.0%)")
    print(f"Returned Results (>0) : {non_zero:,} ({(non_zero / total_searches) * 100:.1f}%)")
    print(f"Zero-Result Searches  : {zero_res:,} ({(zero_res / total_searches) * 100:.1f}%)")
    print(f"Search Result Clicks  : {clicks:,} (CTR: {(clicks / non_zero) * 100:.1f}% on non-zero)")
    print(f"Search-to-Cart Events : {carts:,} (Overall Conversion: {(carts / total_searches) * 100:.2f}%)\n")

    # 1. Zero-Result Query & Typo Recovery Mapping
    zero_df = df[df["results_count"] == 0]
    top_null_queries = zero_df["query"].value_counts().reset_index()
    top_null_queries.columns = ["null_query", "missed_searches"]

    print("Top Zero-Result Queries & Automated Synonym/Typo Mapping:")
    for _, row in top_null_queries.iterrows():
        q = row["null_query"]
        vol = row["missed_searches"]
        matches = get_close_matches(q, ACTIVE_CATALOG_TERMS, n=1, cutoff=0.55)
        suggestion = f"Map synonym -> '{matches[0]}'" if matches else "Escalate to Merchandising (Catalog Gap)"
        print(f"  '{q:20s}' | Volume: {vol:5,d} | Fix: {suggestion}")

    # 2. Ranking Relevance Check (High Results, Low CTR, Deep Click Rank)
    non_zero_summary = (
        df[df["results_count"] > 0]
        .groupby("query")
        .agg(
            searches=("search_id", "count"),
            ctr_pct=("clicked", lambda x: round(x.mean() * 100, 1)),
            atc_pct=("added_to_cart", lambda x: round(x.mean() * 100, 1)),
            avg_click_pos=("clicked_rank", lambda x: round(x.mean(), 1))
        )
        .reset_index()
        .sort_values("ctr_pct")
    )

    print("\nSearch Ranking Bottlenecks (Lowest CTR Despite Available Inventory):")
    print(non_zero_summary.head(3).to_string(index=False))
    print("\nRecommendation: Boost top-converting SKUs for low-CTR queries where avg_click_pos > 6.\n")


if __name__ == "__main__":
    search_logs = simulate_search_logs(35000)
    run_search_audit(search_logs)