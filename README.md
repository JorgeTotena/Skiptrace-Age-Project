# Kentucky Real Estate — Skiptrace Numbers Report

Cleans and prepares skiptrace phone number data for Kentucky real estate calling campaigns, and produces a client-facing analysis report.

- The **All Numbers** file retains every row and is used for analysis.
- The **Deduped** file (one number per property, **oldest** date kept) is imported into the 8020rei domain for property identification.
- The **Numbers Analysis Report** is the styled, client-facing summary of portfolio age and wrong-number exposure.

## Files

| File | Description |
|------|-------------|
| `Extra Call Calling Skipped (13K) Numbers.xlsx` | Source data — raw skiptrace export |
| `Cleaning_File_All_Numbers.xlsx` | Output — all rows, cleaned and transformed; used for analysis |
| `Cleaning_File_Deduped_12K.xlsx` | Output — one number per property (oldest date); imported into 8020rei domain for property identification |
| `Numbers Analysis Report - Internal.xlsx` | Output — internal report with age **and** source breakdowns; do not share with the client |
| `Numbers Analysis Report - Client.xlsx` | Output — client-facing report; age breakdowns only, no source tier information |
| `generate_files.py` | Script that produces all four output files |
| `Initial Requirements.txt` | Original business requirements |
| `notes.md` | Step-by-step process notes and run history |
| `CLAUDE.md` | Instructions for Claude when regenerating files |

## Quick Start

### Requirements
- Python 3.x
- `pandas` and `openpyxl` libraries

```bash
pip install pandas openpyxl
```

### Generate the output files
```bash
python generate_files.py
```

Both output Excel files will be overwritten in place.

## Data Transformations

### SOURCE (tier standardization)
| Raw value | Output |
|-----------|--------|
| T1 / T1Skiptrace / Tier1 / Tier 1 | T1 |
| T2 / T2Skiptrace | T2 |
| T1.2 | T6 |
| T6 | T6 |
| T8 | T8 |
| blank / null | Unknown |

### STATUS
- Blank / null → `Unknown`
- Existing values kept as-is

### Skipped Month-YYYY (added column)
- Derived from `NUMBER CREATED AT`
- Example: `Skipped 2026-04`

### Dedup rule
- Sort by `NUMBER CREATED AT` ascending, then keep the first row per `ID` (i.e. the **oldest** number for each property).

## Numbers Analysis Report (two versions)

Two Excel files are generated, each with two sheets (`Full Portfolio` and `Wrong Numbers`):

- **Internal** (`Numbers Analysis Report - Internal.xlsx`) — age distribution, `SOURCE × age` matrix, and source-aware insights (e.g. the T1/T2 vs T6/T8 sourcing context).
- **Client** (`Numbers Analysis Report - Client.xlsx`) — age distribution and insights only. Source tiers and sourcing history are intentionally stripped.

Shared details:

- `Full Portfolio` **excludes currently-flagged wrong-number properties** (they are re-imported as new records, which would skew the age distribution). Wrong numbers are summarized on their own sheet.
- Age buckets: `<1 year`, `1-2 years`, `2+ years`.
- "Today" for aging is set via the `TODAY` constant in `generate_files.py`.

## Updating the Data
1. Update `Extra Call Calling Skipped (13K) Numbers.xlsx` with new rows
2. (If regenerating on a different date) update `TODAY` in `generate_files.py`
3. Run `python generate_files.py`
4. Log the run in `notes.md` (Run History table)
