
WITH normalized_searches AS (
    SELECT 
        search_id,
        session_id,
        user_id,
        LOWER(TRIM(raw_query_text)) AS clean_query,
        results_returned_count,
        searched_at,
        -- Track if user immediately re-typed another query within 60 seconds
        LEAD(LOWER(TRIM(raw_query_text)), 1) OVER (
            PARTITION BY session_id 
            ORDER BY searched_at ASC
        ) AS next_query_in_session,
        DATEDIFF('second', searched_at, LEAD(searched_at, 1) OVER (
            PARTITION BY session_id 
            ORDER BY searched_at ASC
        )) AS seconds_to_next_search
    FROM clickstream_dw.fct_onsite_searches
    WHERE searched_at >= CURRENT_DATE - INTERVAL '30 DAYS'
      AND TRIM(raw_query_text) <> ''
),

search_engagement AS (
    SELECT 
        s.search_id,
        s.session_id,
        s.clean_query,
        s.results_returned_count,
        CASE WHEN s.results_returned_count = 0 THEN 1 ELSE 0 END AS is_zero_result,
        CASE WHEN s.seconds_to_next_search <= 60 AND s.next_query_in_session <> s.clean_query THEN 1 ELSE 0 END AS was_reformulated,
        MAX(CASE WHEN c.click_id IS NOT NULL THEN 1 ELSE 0 END) AS did_click_result,
        MIN(c.clicked_rank_position) AS top_clicked_rank,
        MAX(CASE WHEN c.added_to_cart = 1 THEN 1 ELSE 0 END) AS did_add_to_cart
    FROM normalized_searches s
    LEFT JOIN clickstream_dw.fct_search_clicks c 
        ON s.search_id = c.search_id
    GROUP BY 
        s.search_id, s.session_id, s.clean_query, 
        s.results_returned_count, s.seconds_to_next_search, s.next_query_in_session
),

query_level_rollup AS (
    SELECT 
        clean_query,
        COUNT(search_id) AS search_volume,
        SUM(is_zero_result) AS zero_result_searches,
        ROUND((SUM(is_zero_result) * 100.0) / COUNT(search_id), 2) AS zero_result_rate_pct,
        ROUND((SUM(was_reformulated) * 100.0) / COUNT(search_id), 2) AS reformulation_rate_pct,
        ROUND((SUM(did_click_result) * 100.0) / NULLIF(COUNT(search_id) - SUM(is_zero_result), 0), 2) AS non_zero_ctr_pct,
        ROUND((SUM(did_add_to_cart) * 100.0) / COUNT(search_id), 2) AS search_to_cart_pct,
        ROUND(AVG(top_clicked_rank), 1) AS avg_clicked_position
    FROM search_engagement
    GROUP BY clean_query
    HAVING COUNT(search_id) >= 50
)

SELECT 
    clean_query,
    search_volume,
    zero_result_rate_pct,
    reformulation_rate_pct,
    non_zero_ctr_pct,
    search_to_cart_pct,
    avg_clicked_position,
    CASE 
        WHEN zero_result_rate_pct >= 50.0 THEN 'CATALOG_OR_SYNONYM_GAP'
        WHEN non_zero_ctr_pct < 18.0 OR avg_clicked_position > 6.0 THEN 'POOR_RELEVANCE_RANKING'
        WHEN non_zero_ctr_pct >= 30.0 AND search_to_cart_pct < 4.0 THEN 'PRICE_OR_STOCK_FRICTION'
        ELSE 'HEALTHY_SEARCH_TERM'
    END AS search_diagnostic_bucket
FROM query_level_rollup
ORDER BY search_volume DESC, search_to_cart_pct ASC;