import json
data = json.load(open("build_consolidated/data.json"))
AGE = ["<1 year", "1-2 years", "2+ years"]
TIERS = ["T1", "T2", "T3", "T6", "T8", "Others", "Unknown"]

tot = sum(r["total"] for r in data.values())
age = {k: sum(r["age_dist"].get(k, 0) for r in data.values()) for k in AGE}
one_plus = age["1-2 years"] + age["2+ years"]

# wrong numbers — only clients that logged STATUS
logged = {c: r for c, r in data.items() if r["wrong_count"] and r["wrong_count"] > 0}
not_logged = [c for c, r in data.items() if not r["wrong_count"]]
wn_tot = sum(r["wrong_count"] for r in logged.values())
wn_base = sum(r["total"] for r in logged.values())
wn_age = {k: sum(r["wrong_age_dist"].get(k, 0) for r in logged.values()) for k in AGE}

# source aggregation across full portfolio
src = {t: {k: 0 for k in AGE + ["Total"]} for t in TIERS}
for r in data.values():
    for s, vals in (r.get("source_full") or {}).items():
        bucket = s if s in TIERS else "Unknown"
        for k in AGE + ["Total"]:
            src[bucket][k] += vals.get(k) or 0

print(f"TOTAL properties: {tot:,}  across {len(data)} clients")
print(f"Age: <1={age['<1 year']:,} ({age['<1 year']/tot:.1%}) | "
      f"1-2={age['1-2 years']:,} ({age['1-2 years']/tot:.1%}) | "
      f"2+={age['2+ years']:,} ({age['2+ years']/tot:.1%})")
print(f"1+ years: {one_plus:,} ({one_plus/tot:.1%})")
print(f"2+ years: {age['2+ years']:,} ({age['2+ years']/tot:.1%})")
print()
print(f"Wrong numbers: {wn_tot:,} across {len(logged)} clients that log STATUS "
      f"(base {wn_base:,}, {wn_tot/wn_base:.2%})")
print(f"  wrong age: <1={wn_age['<1 year']:,} 1-2={wn_age['1-2 years']:,} 2+={wn_age['2+ years']:,}")
print(f"  1+ yr wrong: {wn_age['1-2 years']+wn_age['2+ years']:,} "
      f"({(wn_age['1-2 years']+wn_age['2+ years'])/wn_tot:.1%})")
print(f"  NOT logging STATUS: {not_logged}")
print()
print("SOURCE (full portfolio), sorted by total:")
for t in sorted(TIERS, key=lambda x: -src[x]["Total"]):
    v = src[t]
    if v["Total"]:
        print(f"  {t:8s} total={v['Total']:>9,} ({v['Total']/tot:5.1%})  "
              f"<1={v['<1 year']:>9,}  1-2={v['1-2 years']:>9,}  2+={v['2+ years']:>9,}")

print("\nPer-client (sorted by total):")
print(f"{'client':26s}{'total':>9s}{'<1yr%':>7s}{'1-2%':>7s}{'2+%':>7s}{'1+%':>7s}")
for c, r in sorted(data.items(), key=lambda x: -x[1]["total"]):
    a = r["age_dist"]; t = r["total"]
    lt1 = a.get("<1 year", 0); m = a.get("1-2 years", 0); p2 = a.get("2+ years", 0)
    print(f"{c:26s}{t:>9,}{lt1/t:>7.1%}{m/t:>7.1%}{p2/t:>7.1%}{(m+p2)/t:>7.1%}")
