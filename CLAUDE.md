# Skiptrace Numbers Report — Claude Instructions

## Project Overview
Transforms a raw skiptrace export into cleaned Excel files used for calling campaigns. Currently configured for **Noble Home**. The pipeline is single-client at a time — switching clients means updating `CLIENT_PREFIX`, `PARQUET_FILE`, and `SOURCE_CSV` (or the loader if the source format changes) in `generate_files.py`.

## Source Loader
- Standard: a single CSV in `Input/` (e.g. `Input/noblehome_properties.csv`). First run compiles it into a parquet cache (`Input/<client>_numbers.parquet`); subsequent runs read parquet directly.
- Legacy (Cava): multi-part Excel (`Input/Part *.xlsx`) was supported with a different loader. If a future client ships pre-split Excel parts again, restore that variant.

## Output Files
| File | Purpose |
|------|---------|
| `Cleaning_File_All_Numbers.xlsx` | All rows from source with transformations applied — **used for analysis** |
| `Cleaning_File_Deduped_{N}k.xlsx` | One row per property (oldest phone number date kept) — **imported into 8020rei domain for property identification**. `{N}` = deduped row count rounded to nearest thousand (e.g. `Cleaning_File_Deduped_104k.xlsx`). The filename is generated dynamically; do not hardcode a specific `{N}` anywhere. |
| `Numbers Age Import File.xlsx` | Tagging import file derived from the deduped set. Columns: `folio`, `address`, `zip`, `tag` (the `Skipped YYYY-MM` value). One row per property. |
| `Numbers Analysis Report - Internal.xlsx` | **Internal** report with age + source breakdowns and source-aware insights. Do NOT share with the client. |
| `Numbers Analysis Report - Client.xlsx` | **Client-facing** report with age breakdowns only. No mention of source tiers (T1/T2/T6/T8) or sourcing history. |

## Regeneration
Run `generate_files.py` from the project directory:
```bash
python generate_files.py
```

## Transformation Rules

### SOURCE column mapping
| Original value(s) | Mapped to |
|-------------------|-----------|
| T1, T1Skiptrace, Tier1, Tier 1, IDI, New source Launchskip | T1 |
| T2, T2Skiptrace, SkipForce | T2 |
| Tier 3, Tier3, T3 | T3 |
| T1.2, T6 | T6 |
| T8 | T8 |
| Locate Plus, Lead Sherpa | Others |
| blank / null | See backfill below |

Note: `Tier3` (no space) was added for Noble Home — they use the no-space variant exclusively. `Tier 3` (with space) is also kept for older clients.

**TAGS backfill (when SOURCE is blank):** the script inspects the `TAGS` column for tier indicators before giving up. Check order: `T1.2` → T6, `T8` → T8, `T6` → T6, `T2` → T2, `T1` / `Tier1` / `Tier 1` → T1. Only rows with no tier signal in either column end up as `Unknown`.

### STATUS column
- Blank or null → `Unknown`
- Existing values are kept as-is (the `wrong_number` tag does not override STATUS)

### Skipped Month-YYYY column (new)
- Derived from `NUMBER CREATED AT`
- Format: `Skipped YYYY-MM` (e.g. `Skipped 2026-04`)

### Runtime constants — must stay dynamic
- **TODAY**: read from the system clock at run time (`pd.Timestamp.today().normalize()`). Do not pin to a specific date.
- **Deduped filename**: computed from `len(df_dedup)` (rounded to nearest thousand + `k`). Do not hardcode `12K` / `104k` etc.

### Deduped file logic
- Sort all rows by `NUMBER CREATED AT` ascending
- Keep the first (oldest) row per property (composite key: `FOLIO + ADDRESS + ZIP`). This composite key is the standard going forward; older client variants used an `ID` column.
- Result: one phone number per property (the earliest-skiptraced number)

### Wrong-number signal
- Standard for current clients (Cava, Noble Home): `STATUS == 'Wrong Number'`. TAGS does not carry the signal.
- Kentucky used `wrong_number` in the `TAGS` column. Switch detection logic in `clean()` if a future client uses that pattern.

### Numbers Analysis Report (two versions)
- **Internal** (`Numbers Analysis Report - Internal.xlsx`): age + SOURCE × age matrix + source-aware insights
- **Client** (`Numbers Analysis Report - Client.xlsx`): age only. Source tiers and sourcing history are stripped — the client is not aware that sourcing has changed over time
- Both have two sheets: `Full Portfolio` and `Wrong Numbers`
- `Full Portfolio` **includes all deduped properties** (totals match the deduped Excel file). Wrong-number properties are also broken out on their own sheet for detail
- Age buckets: `<1 year`, `1-2 years`, `2+ years`
- "Age" = how long ago the property's skiptraced number was obtained (today − `NUMBER CREATED AT`)
- Wrong-number properties are identified by `wrong_number` appearing in the `TAGS` column of any row for that property (computed from the full non-deduped dataset)
- Do NOT mention "oldest number kept" in the client version — use neutral wording like "one record per property"

## Source File Columns
Noble Home: `Property ID`, `FOLIO`, `ADDRESS`, `ZIP`, `TAGS`, `NUMBER`, `SOURCE`, `STATUS`, `NUMBER CREATED AT` (no `ID` column — the composite `FOLIO+ADDRESS+ZIP` is the property key).
Older variants may include an `ID` column; the script does not depend on it.
