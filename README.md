# E-Commerce Search Relevance & Zero-Result Query Analytics

An onsite search analytics pipeline that diagnoses search-to-cart drop-offs, separates catalog gaps from ranking failures, and maps high-volume typo/synonym queries to active inventory.

## Problem Context
Onsite search users convert at 2x–3x the rate of casual browsers, yet strict keyword matching often returns "0 Results Found" for minor spelling errors or regional synonyms (e.g., "earpods" vs "earbuds", "cover" vs "case"). Additionally, queries with poor ranking relevance force users to scroll past position 6, hurting add-to-cart rates.

## Files
- `search_funnel_pipeline.sql`: Normalizes search strings, tracks 60-second query reformulations via `LEAD()`, and classifies search terms into actionable diagnostic buckets.
- `search_relevance_audit.py`: Evaluates 35k+ search sessions, audits CTR and click-rank position bias, and matches null queries against catalog terms using fuzzy string similarity.
- `requirements.txt`: Python dependencies.

## Diagnostic Framework
1. **Query Normalization & Reformulation:** Standardizes casing/whitespace and uses windowed `LEAD()` to detect when users immediately re-type a failed query within 60 seconds.
2. **Zero-Result Typo & Synonym Recovery:** Uses sequence matching (`difflib`) to distinguish true missing catalog items from spelling/synonym mismatches that can be fixed via search dictionary rules.
3. **Position Bias & Ranking Audit:** Flags terms with healthy result counts (`>0`) but low CTR (`<18%`) and deep average click ranks (`>6.0`) for search ranking re-weighting.

## How to Run

```bash
git clone https://github.com/puneetgoswami1/ecommerce-search-funnel-analytics.git
cd ecommerce-search-funnel-analytics

pip install -r requirements.txt
python search_relevance_audit.py