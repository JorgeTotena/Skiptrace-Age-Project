"""Extract structured metrics from the 11 per-client Numbers Analysis Reports.

Each report (Internal + Client) has two sheets: 'Full Portfolio' and 'Wrong Numbers'.
We parse by scanning column 0 for known labels and reading the age-distribution and
source x age tables positionally. Output: build_consolidated/data.json
"""
import pandas as pd, glob, os, re, json

INT_DIR = "Reports/Internal"
EXT_DIR = "Reports/External"

CLIENTS = [
    "As Is Homebuyers", "Atlas Property Investors", "Atlas Residential", "Cava",
    "Kentucky Real Estate", "Leave the Key", "Noble Home", "Patriot Home Buyers",
    "Pillar Home Buyers", "Rapid Fire HB", "Vegas Cash Offers",
]

AGE_KEYS = ["<1 year", "1-2 years", "2+ years"]


def to_int(x):
    if pd.isna(x):
        return None
    s = re.sub(r"[^\d]", "", str(x))
    return int(s) if s else None


def parse_paren(s):
    """'478,091  (87.8%)' -> (478091, 87.8)"""
    if pd.isna(s):
        return None, None
    s = str(s)
    cnt = re.search(r"[\d,]+", s)
    pct = re.search(r"([\d.]+)%", s)
    return (int(cnt.group().replace(",", "")) if cnt else None,
            float(pct.group(1)) if pct else None)


def find_label(df, *labels):
    """Return value in col 1 for first row whose col0 starts with any label."""
    for _, row in df.iterrows():
        c0 = str(row[0]).strip()
        for lab in labels:
            if c0.startswith(lab):
                return row[1]
    return None


def parse_age_table(df):
    """Find 'Data age' header row, read the 3 bucket rows -> {bucket: count}."""
    out = {}
    rows = df.reset_index(drop=True)
    for i in range(len(rows)):
        if str(rows.iloc[i, 0]).strip() == "Data age":
            for j in range(i + 1, min(i + 6, len(rows))):
                key = str(rows.iloc[j, 0]).strip()
                if key in AGE_KEYS:
                    out[key] = to_int(rows.iloc[j, 1])
                if key == "Total":
                    break
            break
    return out


def parse_source_table(df):
    """Find 'SOURCE' header row, read source rows until 'Total'.
    Returns {source: {'<1 year':n,'1-2 years':n,'2+ years':n,'Total':n}}."""
    out = {}
    rows = df.reset_index(drop=True)
    for i in range(len(rows)):
        if str(rows.iloc[i, 0]).strip() == "SOURCE":
            for j in range(i + 1, len(rows)):
                src = str(rows.iloc[j, 0]).strip()
                if src == "Total" or src in ("nan", ""):
                    break
                out[src] = {
                    "<1 year": to_int(rows.iloc[j, 1]),
                    "1-2 years": to_int(rows.iloc[j, 2]),
                    "2+ years": to_int(rows.iloc[j, 3]),
                    "Total": to_int(rows.iloc[j, 4]),
                }
            break
    return out


def parse_subtitle_range(df):
    """Row 1 col0 holds 'Generated YYYY-MM-DD ... Data range: A to B'."""
    txt = str(df.iloc[1, 0])
    gen = re.search(r"Generated\s+(\d{4}-\d{2}-\d{2})", txt)
    rng = re.search(r"Data range:\s*(\d{4}-\d{2}-\d{2})\s*to\s*(\d{4}-\d{2}-\d{2})", txt)
    return {
        "generated": gen.group(1) if gen else None,
        "range_start": rng.group(1) if rng else None,
        "range_end": rng.group(2) if rng else None,
    }


def parse_report(path, internal):
    fp = pd.read_excel(path, sheet_name="Full Portfolio", header=None)
    wn = pd.read_excel(path, sheet_name="Wrong Numbers", header=None)

    total = to_int(find_label(fp, "Total properties in portfolio",
                              "Active properties in portfolio"))
    one_plus = parse_paren(find_label(fp, "Properties with data 1+ years old"))
    two_plus = parse_paren(find_label(fp, "Properties with data 2+ years old"))

    wn_count = to_int(find_label(wn, "Wrong-number properties"))
    wn_share = parse_paren(find_label(wn, "Share of portfolio", "Share of original portfolio"))

    rec = {
        "total": total,
        "one_plus_count": one_plus[0], "one_plus_pct": one_plus[1],
        "two_plus_count": two_plus[0], "two_plus_pct": two_plus[1],
        "age_dist": parse_age_table(fp),
        "wrong_count": wn_count,
        "wrong_share_pct": wn_share[1],
        "wrong_age_dist": parse_age_table(wn),
        "meta": parse_subtitle_range(fp),
    }
    if internal:
        rec["source_full"] = parse_source_table(fp)
        rec["source_wrong"] = parse_source_table(wn)
    return rec


data = {}
for c in CLIENTS:
    ip = os.path.join(INT_DIR, f"{c} - Numbers Analysis Report - Internal.xlsx")
    ep = os.path.join(EXT_DIR, f"{c} - Numbers Analysis Report - Client.xlsx")
    rec = parse_report(ip, internal=True)
    # cross-check total against external
    if os.path.exists(ep):
        ext = parse_report(ep, internal=False)
        rec["ext_total"] = ext["total"]
    data[c] = rec

with open("build_consolidated/data.json", "w") as f:
    json.dump(data, f, indent=2)

# sanity print
print(f"{'client':26s} {'total':>9s} {'1+%':>6s} {'2+%':>6s} {'wrong':>8s} {'w%':>5s}  sources")
for c, r in data.items():
    srcs = ",".join(sorted((r.get("source_full") or {}).keys()))
    ext_flag = "" if r.get("ext_total") == r["total"] else f"  EXT_MISMATCH({r.get('ext_total')})"
    print(f"{c:26s} {r['total']:>9,} {r['one_plus_pct'] or 0:>6} {r['two_plus_pct'] or 0:>6} "
          f"{r['wrong_count'] or 0:>8,} {r['wrong_share_pct'] or 0:>5}  {srcs}{ext_flag}")

# verify age_dist sums to total
print("\nAge-dist sum check:")
for c, r in data.items():
    s = sum(v for v in r["age_dist"].values() if v)
    flag = "OK" if s == r["total"] else f"MISMATCH sum={s}"
    print(f"  {c:26s} {flag}")
