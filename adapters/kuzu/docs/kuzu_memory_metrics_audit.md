# Kuzu Memory Metrics Audit

Input CSV: `results/kuzu/kuzu_sf10_0_to_sf10_4_final_results_hz1000_median_replaced.csv`
Summary CSV: `adapters/kuzu/docs/kuzu_memory_metrics_audit.md`

## Finding

The current `mem_peak_mb` and `mem_avg_mb` columns are not reliable per-query memory metrics. They were collected as resident memory of the long-lived Python/Kuzu process while one database object was reused across many queries. The values therefore include Kuzu buffer/cache state and allocations left by earlier queries.

This explains the repeated values seen in the Excel file: short queries often have only one or a few RSS samples, and when the process RSS does not move, peak and average are identical. Consecutive queries can also inherit the previous steady RSS value, so the previous average can equal the next peak or average.

## Highest-Risk Groups

| Dataset | Suite | Rows | Peak=Avg | Duplicate Pair Rows | Adjacent Same Pair | Examples |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| sf10_0 | Shortest_Path_Queries | 15 | 15 (100.0%) | 15 (100.0%) | 12 | 1a.sql -> 1b.sql same pair 232.010/232.010 <br> 1a.sql avg == 1b.sql peak (232.010) <br> 1b.sql -> 1c.sql same pair 232.010/232.010 <br> 1b.sql avg == 1c.sql peak (232.010) <br> 1c.sql -> 2a.sql same pair 232.010/232.010 <br> 1c.sql avg == 2a.sql peak (232.010) |
| sf10_2 | Shortest_Path_Queries | 15 | 14 (93.33%) | 13 (86.67%) | 10 | 1b.sql -> 1c.sql same pair 299.035/299.035 <br> 1b.sql avg == 1c.sql peak (299.035) <br> 1c.sql -> 2a.sql same pair 299.035/299.035 <br> 1c.sql avg == 2a.sql peak (299.035) <br> 2a.sql -> 2b.sql same pair 299.035/299.035 <br> 2a.sql avg == 2b.sql peak (299.035) |
| sf10_1 | Shortest_Path_Queries | 15 | 13 (86.67%) | 13 (86.67%) | 11 | 1b.sql -> 1c.sql same pair 247.477/247.477 <br> 1b.sql avg == 1c.sql peak (247.477) <br> 1c.sql -> 2a.sql same pair 247.477/247.477 <br> 1c.sql avg == 2a.sql peak (247.477) <br> 2a.sql -> 2b.sql same pair 247.477/247.477 <br> 2a.sql avg == 2b.sql peak (247.477) |
| sf10_3 | Shortest_Path_Queries | 15 | 14 (93.33%) | 12 (80.0%) | 9 | 1b.sql -> 1c.sql same pair 489.798/489.798 <br> 1b.sql avg == 1c.sql peak (489.798) <br> 1c.sql -> 2a.sql same pair 489.798/489.798 <br> 1c.sql avg == 2a.sql peak (489.798) <br> 2b.sql -> 2c.sql same pair 494.954/494.954 <br> 2b.sql avg == 2c.sql peak (494.954) |
| sf10_1 | main_queries | 96 | 72 (75.0%) | 66 (68.75%) | 48 | 6b.sql -> 6c.sql same pair 2557.261/2557.261 <br> 6b.sql avg == 6c.sql peak (2557.261) <br> 7b.sql -> 7c.sql same pair 2567.573/2567.573 <br> 7b.sql avg == 7c.sql peak (2567.573) <br> 9c.sql -> 10a.sql same pair 2634.598/2634.598 <br> 9c.sql avg == 10a.sql peak (2634.598) |
| sf10_0 | main_queries | 96 | 64 (66.67%) | 58 (60.42%) | 45 | 9c.sql -> 10a.sql same pair 1551.886/1551.886 <br> 9c.sql avg == 10a.sql peak (1551.886) <br> 10a.sql -> 10b.sql same pair 1551.886/1551.886 <br> 10a.sql avg == 10b.sql peak (1551.886) <br> 10b.sql -> 10c.sql same pair 1551.886/1551.886 <br> 10b.sql avg == 10c.sql peak (1551.886) |

## Resolution

Use per-query process isolation for memory measurements. A corrected run should open Kuzu in a fresh child process, take `rss_baseline_mb` after database and connection creation, start timing immediately before the query, and report both absolute process RSS and `mem_*_delta_mb` relative to that baseline. The existing elapsed-time values remain useful as wall-clock timings, but the legacy memory columns should not be used for cross-query or cross-SF comparisons.
