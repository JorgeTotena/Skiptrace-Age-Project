# Project Notes — Skiptrace Numbers Report

## What This Project Does
Cleans and deduplicates a skiptrace export for a Kentucky real estate calling campaign, and produces both an internal and a client-facing analysis report.
Four output files are generated from one source spreadsheet.

## Steps to Generate the Files

### 1. Drop the new source export into the project folder
- The script picks up the **newest** `*.csv` or `*.xlsx` in the project directory automatically (it ignores its own outputs). Any name works — no need to rename files or edit the script.
- Current working source (as of 2026-04-23): `kentuckyrealestate_numbers_properties_2026-04-20.csv`.

### 2. Run the generation script
```bash
cd "F:\8020\Kentucky Real Estate\Skiptrace_numbers_report"
python generate_files.py
```

### 3. What the script does
1. Auto-discovers the newest source file in the directory (CSV or XLSX)
2. Converts `NUMBER CREATED AT` to proper datetime
3. Applies STATUS rules:
   - Blank/null STATUS → `Unknown`
   - Existing STATUS values are kept as-is
4. Maps SOURCE values to standardized tiers (T1, T2, T6, T8, Unknown). When the SOURCE cell is blank, recovers the tier from `TAGS` (e.g., `T1Skiptrace`, `T6Skiptrace`, `T1.2`, `Tier1`) before falling back to `Unknown`
5. Adds `Skipped Month-YYYY` column formatted as `Skipped YYYY-MM`
6. Saves **All Numbers** file (all rows, all transformations)
7. Saves **Deduped** file (one row per property ID, **oldest** date wins). Filename is generated dynamically as `Cleaning_File_Deduped_{N}k.xlsx` where N is the deduped row count rounded to the nearest thousand (e.g. 104k for 103,802 rows)
8. Builds age and source breakdowns and saves **two** analysis reports: an **Internal** version (with source detail) and a **Client** version (no source detail). The "Generated" date printed on both reports uses today's date at run time

## Output Summary
- `Cleaning_File_All_Numbers.xlsx` — full dataset, cleaned; **used for analysis**
- `Cleaning_File_Deduped_{N}k.xlsx` — one number per property (oldest); **imported into the 8020rei domain for property identification**. Filename reflects the current deduped row count (e.g. `Cleaning_File_Deduped_104k.xlsx`)
- `Numbers Analysis Report - Internal.xlsx` — internal deliverable; age + `SOURCE × age` + source-aware insights
- `Numbers Analysis Report - Client.xlsx` — client-facing deliverable; age breakdowns and insights only, no source tier information

## Run History
| Date | Source Rows | All Numbers Rows | Deduped Rows | Notes |
|------|-------------|------------------|--------------|-------|
| 2026-04-20 | 109,566 | 109,566 | 12,877 | Second run after source data added (newest-per-ID dedup) |
| 2026-04-21 | 109,566 | 109,566 | 12,877 | Switched dedup to oldest-per-ID; added `Numbers Analysis Report.xlsx` |
| 2026-04-21 | 109,566 | 109,566 | 12,877 | Split report into Internal (with sources) and Client (no sources) versions; Full Portfolio now excludes wrong-number properties; age buckets collapsed to `<1 / 1-2 / 2+ years` |
| 2026-04-23 | 851,766 | 851,766 | 103,802 | Switched to full-portfolio export (`kentuckyrealestate_numbers_properties_2026-04-20.csv`). De-hardcoded: source file auto-discovered, `TODAY` from system clock, deduped filename dynamic (`Cleaning_File_Deduped_104k.xlsx`). Added SOURCE backfill from TAGS (shrank `Unknown` from ~116K raw rows with blank SOURCE to 21 deduped properties). |

## Notes & Decisions
- Source file is auto-discovered (newest CSV/XLSX in the project dir). `TODAY` is read from the system clock at run time. Deduped output filename is generated from the deduped row count. Nothing project-specific is hardcoded, so another teammate can drop a fresh export in and re-run without edits.
- The SOURCE column is overwritten with the mapped tier value (original values not preserved). If the SOURCE cell is blank, the script recovers the tier from the `TAGS` column (matching `T1.2` → T6, then `T8`/`T6`/`T2` word tokens, then `T1` / `Tier1` / `Tier 1`). Only rows where neither SOURCE nor TAGS carry a tier indicator end up as `Unknown`.
- The `wrong_number` tag in TAGS does **not** affect STATUS — only blank/null values are changed to `Unknown`.
- Dedup keeps the row with the **oldest** `NUMBER CREATED AT` per `ID` (changed 2026-04-21 — was newest). If a tie exists, the first row encountered after sort is kept.
- Because dedup keeps the oldest row, the STATUS column on the deduped file is almost entirely `Unknown` — wrong-number dispositions recorded on newer rows are not carried into the deduped file. Wrong-number detection for the report is derived from the full (non-deduped) dataset via the TAGS column.
- The `Skipped Month-YYYY` column name follows the original requirement; the actual format stored is `Skipped YYYY-MM`.
- Report age buckets: `<1 year`, `1-2 years`, `2+ years`. "Age" is computed as `(TODAY − NUMBER CREATED AT).days / 365.25` on the property's oldest skiptraced number. `TODAY` floats with the system date — if you need to reproduce a historical run exactly, snapshot or pin it manually.
- Full Portfolio sheet counts = raw oldest-per-ID counts **minus** wrong-number properties in each bucket. A property is never counted on both sheets.

### 2026-04-21 run reconciliation (13K dataset)
| Bucket | Full Portfolio | Wrong Numbers | Total |
|---|---:|---:|---:|
| <1 year | 3,519 | 150 | 3,669 |
| 1-2 years | 3,083 | 239 | 3,322 |
| 2+ years | 5,505 | 381 | 5,886 |
| **Total** | **12,107** | **770** | **12,877** |

### 2026-04-23 run reconciliation (full 104K portfolio)
| Bucket | Full Portfolio | Wrong Numbers | Total |
|---|---:|---:|---:|
| <1 year | 26,156 | 150 | 26,306 |
| 1-2 years | 27,036 | 239 | 27,275 |
| 2+ years | 49,840 | 381 | 50,221 |
| **Total** | **103,032** | **770** | **103,802** |

Deduped SOURCE distribution after TAGS backfill: T1 = 85,828 · T6 = 9,168 · T8 = 7,989 · T2 = 796 · Unknown = 21.

## Client Context
- 2026-04-21: Client reported a ~29% unusable rate (640 wrong numbers + 553 N/A out of 2,200 dialed) on the 13K batch and asked for a root-cause explanation. The analysis report was used to respond — the root cause identified is data age, with 70.9% of the portfolio carrying contact data 1+ years old and 80.5% of currently-flagged wrong numbers sitting on 1+ year old data.
- Recommended response framing: re-skiptrace the 2+ year cohort in parallel with ongoing dialing (not a pause), then run a second pass on refreshed numbers. Establish a rolling refresh cadence on 2+ year records going forward.
- When sending to the client, attach **`Numbers Analysis Report - Client.xlsx`** (no source detail). The Internal version must not leave the team.
