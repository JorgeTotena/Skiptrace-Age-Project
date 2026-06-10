"""Generate per-client Skiptrace Health Cards (client-facing) + one internal CSM
Playbook from the consolidated metrics in data.json.

- Client cards: age-only, no source tiers, no sourcing history, NO health score.
  (Same client-safe rules as the 'Client' analysis report.)
- Playbook: INTERNAL — includes CS health score, urgency ranking, talking points.

Recommendations are produced by a small rules engine over each client's age +
wrong-number profile, so every client gets a tailored card. Run from project root:
    python build_consolidated/build_recommendations.py
"""
import json
import os
from datetime import date, datetime

DATA = "build_consolidated/data.json"
OUT_DIR = "Reports/Recommendations"
TODAY = date.today().strftime("%Y-%m-%d")

# Clients explicitly out of scope.
EXCLUDE = {"Atlas Residential"}

# CS health context (internal only — used in the Playbook, never on client cards).
# AI health score 1-5: 5 Thriving, 4 Healthy, 3 At Risk, 2 Poor, 1 Critical.
# Pulled from the 8020REI Clients Data source; refresh when scores change.
HEALTH = {
    "Patriot Home Buyers":      {"score": 1, "csm": "Lauren Oxman",   "mrr": 2276.30, "status": "Active"},
    "Leave the Key":            {"score": 3, "csm": "Victoria Solis",  "mrr": 1287.50, "status": "Active"},
    "Cava":                     {"score": 3, "csm": "Victoria Solis",  "mrr": 1416.25, "status": "Active"},
    "Rapid Fire HB":            {"score": 3, "csm": "Victoria Solis",  "mrr": 6470.46, "status": "Active"},
    "Kentucky Real Estate":     {"score": 4, "csm": "Victoria Solis",  "mrr": 2224.80, "status": "Active"},
    "Noble Home":               {"score": 4, "csm": "Victoria Solis",  "mrr": 3020.00, "status": "Active"},
    "Pillar Home Buyers":       {"score": 3, "csm": "Victoria Solis",  "mrr": 1606.80, "status": "Active"},
    "Atlas Property Investors": {"score": 3, "csm": "Lauren Oxman",   "mrr": 3380.00, "status": "Active"},
    "As Is Homebuyers":         {"score": 2, "csm": "Andrea Castano",  "mrr": 2300.00, "status": "Active"},
    "Vegas Cash Offers":        {"score": 1, "csm": "Victoria Solis",  "mrr": 1890.00, "status": "Canceled"},
}
SCORE_LABEL = {1: "Critical", 2: "Poor", 3: "At Risk", 4: "Healthy", 5: "Thriving"}
SCORE_CLASS = {1: "hs1", 2: "hs2", 3: "hs3", 4: "hs4", 5: "hs4"}


def fmt_range(meta):
    def mon(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").strftime("%b %Y")
        except (ValueError, TypeError):
            return "?"
    return f"{mon(meta.get('range_start'))} – {mon(meta.get('range_end'))}"


def metrics(name, rec):
    total = rec["total"]
    ad = rec["age_dist"]
    under1 = ad.get("<1 year", 0) or 0
    one_two = ad.get("1-2 years", 0) or 0
    two_plus = ad.get("2+ years", 0) or 0
    pct = lambda n: (n / total * 100) if total else 0.0
    return {
        "name": name,
        "total": total,
        "under1": under1, "one_two": one_two, "two_plus": two_plus,
        "under1_pct": pct(under1), "one_two_pct": pct(one_two), "two_plus_pct": pct(two_plus),
        "one_plus_count": rec.get("one_plus_count") or (one_two + two_plus),
        "one_plus_pct": rec.get("one_plus_pct") or pct(one_two + two_plus),
        "two_plus_count": rec.get("two_plus_count") or two_plus,
        "wrong_count": rec.get("wrong_count") or 0,
        "wrong_share": rec.get("wrong_share_pct") or 0.0,
        "range": fmt_range(rec.get("meta", {})),
    }


def archetype(m):
    wp, tp, op = m["wrong_share"], m["two_plus_pct"], m["one_plus_pct"]
    if wp >= 15:
        return "wrong"
    if tp >= 40:
        return "stale_heavy"
    if wp >= 10:
        return "wrong"
    if tp >= 15:
        return "stale_moderate"
    if tp < 15 and op >= 65:
        return "aging"
    return "healthy"


def headline(m, arch):
    tp, op, u1, wp = m["two_plus_pct"], m["one_plus_pct"], m["under1_pct"], m["wrong_share"]
    if arch == "wrong":
        return f"{wp:.1f}%", "of your dialed numbers are flagged as wrong numbers — a cleanup is the fastest win available to you."
    if arch == "stale_heavy":
        return f"{tp:.1f}%", "of your contact data is 2+ years old — the largest refresh opportunity in your portfolio."
    if arch == "stale_moderate":
        return f"{tp:.1f}%", "of your contact data is 2+ years old and climbing — a good time to plan a refresh."
    if arch == "aging":
        return f"{op:.1f}%", "of your contact data is now 1+ year old, with a large group about to cross the 2-year mark — a refresh wave is approaching."
    # healthy
    if tp < 5:
        return f"{tp:.0f}%", "of your contact data is 2+ years old — your portfolio is among the freshest we manage."
    return f"{u1:.0f}%", "of your contact data was gathered in the last year — your portfolio is in good shape."


def means_text(m, arch):
    base_stale = ("Phone numbers go stale as people change carriers and move. Records gathered 2+ years ago "
                  "connect at meaningfully lower rates and produce more disconnected or wrong numbers on the dial. "
                  "A targeted refresh of the oldest records is the highest-impact step to lift your connect rate.")
    if arch in ("stale_heavy", "stale_moderate"):
        return base_stale
    if arch == "aging":
        return ("Most of your numbers are now over a year old, and a large group is about to cross the two-year "
                "mark, where connect rates drop off. Refreshing before that wave hits keeps your reachable-number "
                "count high and your dialer productive.")
    if arch == "wrong":
        extra = " On top of that, a large share of your data is 2+ years old, so a refresh and a cleanup go hand in hand." if m["two_plus_pct"] >= 40 else ""
        return ("A high share of your dialed numbers are coming back as wrong numbers. These are usually stale "
                "records that a fresh skiptrace can recover — cleaning them up protects caller productivity and "
                "your connect rate." + extra)
    return ("Your contact data is fresh relative to the portfolios we manage, and fresh numbers connect at higher "
            "rates. The priority here is simply maintaining that edge with a steady refresh cadence.")


def recommendations(m, arch):
    """Return up to 3 (title, body) recs, ranked by a weight per the client's profile."""
    cands = []
    tp, wp = m["two_plus_pct"], m["wrong_share"]
    if m["two_plus"] and tp >= 10:
        cands.append((100 + tp, "Refresh your oldest records first",
                      f"The {m['two_plus']:,} properties with 2+ year-old data are the priority cohort — "
                      f"re-skiptracing these is where a fresh pull recovers the most reachable numbers."))
    if m["wrong_count"] and wp >= 5:
        cands.append((90 + wp * 2, "Run a wrong-number cleanup",
                      f"{m['wrong_count']:,} numbers ({wp:.1f}% of your portfolio) are flagged as wrong. Submit the "
                      f"older ones to a fresh skiptrace and recycle the recovered numbers back into the dialer."))
    if m["one_two"] and m["one_two_pct"] >= 5:
        cands.append((50 + min(m["one_two_pct"], 35), "Put the 1–2 year band on a rolling refresh",
                      f"{m['one_two']:,} records are approaching the stale window. Refreshing them on a regular "
                      f"cadence keeps your portfolio weighted toward higher-yield data."))
    if m["wrong_count"] == 0:
        cands.append((40, "Turn on wrong-number tracking in your dialer",
                      "No wrong-number dispositions are being captured today — enabling this lets us measure and "
                      "automatically clean bad numbers going forward."))
    if m["wrong_count"] and 0 < wp < 5:
        cands.append((20, "Keep wrong numbers in check",
                      f"{m['wrong_count']:,} numbers ({wp:.1f}%) are flagged — a low rate. Periodically recycling "
                      f"them through a fresh skiptrace keeps caller productivity high."))
    maintain_w = 65 if arch == "healthy" else 10
    cands.append((maintain_w, "Maintain your current refresh cadence",
                  "Your contact data is in good shape. Keep your current cadence and we'll re-check the age profile "
                  "in about six months."))
    cands.sort(key=lambda x: x[0], reverse=True)
    return [(t, b) for _, t, b in cands[:3]]


# ---------- HTML ----------
CARD_CSS = """
  @page { size: letter; margin: 0; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; color: #2b2b2b; background: #eef2f6; }
  .card { width: 8.5in; min-height: 11in; margin: 0 auto; background: #fff; padding: 0.7in 0.8in; }
  .top { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #1F4E78; padding-bottom: 14px; }
  .brand { font-size: 13px; letter-spacing: 2px; color: #5B9BD5; font-weight: 700; text-transform: uppercase; }
  .client { font-size: 26px; font-weight: 700; color: #1F4E78; margin-top: 2px; }
  .meta { font-size: 11px; color: #888; text-align: right; line-height: 1.5; }
  .headline { background: #1F4E78; color: #fff; border-radius: 10px; padding: 22px 26px; margin: 26px 0 8px; }
  .headline .big { font-size: 40px; font-weight: 800; line-height: 1; }
  .headline .sub { font-size: 15px; opacity: .9; margin-top: 8px; }
  .cum { display: flex; gap: 16px; margin-top: 14px; }
  .cbox { flex: 1; border: 1px solid #e3e9ef; border-radius: 8px; padding: 14px 18px; text-align: center; }
  .cbox .cv { font-size: 30px; font-weight: 800; color: #1F4E78; line-height: 1; }
  .cbox .cv.red { color: #C0504D; }
  .cbox .cl { font-size: 12px; color: #666; margin-top: 7px; line-height: 1.4; }
  .cbox .cl span { color: #999; font-size: 11px; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #1F4E78; margin: 26px 0 10px; }
  .bar { display: flex; height: 38px; border-radius: 6px; overflow: hidden; font-size: 12px; color: #fff; font-weight: 600; }
  .seg { display: flex; align-items: center; justify-content: center; }
  .s1 { background: #2E9E5B; } .s2 { background: #E0A93B; } .s3 { background: #C0504D; }
  .legend { display: flex; gap: 22px; margin-top: 10px; font-size: 12px; color: #555; flex-wrap: wrap; }
  .legend span { display: inline-block; width: 11px; height: 11px; border-radius: 2px; margin-right: 6px; vertical-align: middle; }
  .means { background: #f5f8fb; border-left: 4px solid #5B9BD5; padding: 14px 16px; font-size: 13.5px; line-height: 1.55; color: #333; border-radius: 4px; }
  .rec { display: flex; gap: 14px; align-items: flex-start; margin: 12px 0; }
  .num { flex: 0 0 30px; height: 30px; border-radius: 50%; background: #1F4E78; color: #fff; font-weight: 700; display: flex; align-items: center; justify-content: center; font-size: 15px; }
  .rec .body { font-size: 13.5px; line-height: 1.5; }
  .rec .body b { color: #1F4E78; }
  .foot { margin-top: 34px; border-top: 1px solid #e2e2e2; padding-top: 12px; font-size: 10.5px; color: #999; text-align: center; }
"""


def seg(pct, cls, label):
    if pct <= 0:
        return ""
    txt = label if pct >= 9 else ""
    return f'<div class="seg {cls}" style="width:{pct:.2f}%">{txt}</div>'


def render_card(m, arch):
    big, sub = headline(m, arch)
    recs = recommendations(m, arch)
    rec_html = "".join(
        f'<div class="rec"><div class="num">{i}</div><div class="body"><b>{t}.</b> {b}</div></div>'
        for i, (t, b) in enumerate(recs, 1)
    )
    bar = (seg(m["under1_pct"], "s1", "") +
           seg(m["one_two_pct"], "s2", f'1–2 yrs · {m["one_two_pct"]:.1f}%') +
           seg(m["two_plus_pct"], "s3", f'2+ years · {m["two_plus_pct"]:.1f}%'))
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{m['name']} — Contact Data Health Card</title>
<style>{CARD_CSS}</style></head><body>
<div class="card">
  <div class="top">
    <div><div class="brand">8020REI · Skiptrace Data Review</div><div class="client">{m['name']}</div></div>
    <div class="meta">Prepared {TODAY}<br>Portfolio: {m['total']:,} properties<br>Data range: {m['range']}</div>
  </div>
  <div class="headline"><div class="big">{big}</div><div class="sub">{sub}</div></div>
  <div class="cum">
    <div class="cbox"><div class="cv">{m['one_plus_pct']:.1f}%</div><div class="cl">is <b>1+ year</b> old<br><span>{m['one_plus_count']:,} properties</span></div></div>
    <div class="cbox"><div class="cv red">{m['two_plus_pct']:.1f}%</div><div class="cl">is <b>2+ years</b> old<br><span>{m['two_plus_count']:,} properties</span></div></div>
  </div>
  <h2>How fresh is your contact data?</h2>
  <div class="bar">{bar}</div>
  <div class="legend">
    <div><span class="s1"></span>Under 1 year — {m['under1']:,} ({m['under1_pct']:.1f}%)</div>
    <div><span class="s2"></span>1–2 years — {m['one_two']:,} ({m['one_two_pct']:.1f}%)</div>
    <div><span class="s3"></span>2+ years — {m['two_plus']:,} ({m['two_plus_pct']:.1f}%)</div>
  </div>
  <h2>What this means</h2>
  <div class="means">{means_text(m, arch)}</div>
  <h2>Recommended next steps</h2>
  {rec_html}
  <div class="foot">Prepared by 8020REI for {m['name']} · One record per property · Confidential</div>
</div></body></html>"""


def talking_point(m, arch):
    h = HEALTH.get(m["name"], {})
    if h.get("status") == "Canceled":
        return "Canceled. Data was clean &amp; fresh — a useful proof point in a win-back conversation."
    if arch == "wrong":
        tp_note = f" Plus {m['two_plus_pct']:.0f}% is 2+ yrs old — cleanup + refresh together." if m["two_plus_pct"] >= 40 else ""
        msg = f'"{m["wrong_share"]:.0f}% of your numbers are flagged wrong — a cleanup is the fastest win."{tp_note}'
    elif arch == "stale_heavy":
        msg = f'"{m["two_plus_pct"]:.0f}% of your numbers are 2+ yrs old — let\'s refresh the oldest {m["two_plus_count"]:,}."'
    elif arch == "stale_moderate":
        msg = f'"{m["two_plus_pct"]:.0f}% is 2+ yrs old and climbing — plan a refresh now."'
    elif arch == "aging":
        msg = f'"{m["one_two"]:,} numbers are about to cross the 2-yr mark — get ahead with a rolling refresh."'
    else:
        msg = f'"Freshest portfolio — maintain cadence; light refresh of the {m["two_plus_count"]:,} oldest."'
    if h.get("score", 5) <= 2:
        msg += " <b>At-risk account — pair with the retention play.</b>"
    return msg


def urgency(m):
    h = HEALTH.get(m["name"], {})
    score = h.get("score", 5)
    aging_bonus = 15 if (m["two_plus_pct"] < 15 and m["one_plus_pct"] >= 65) else 0
    return m["two_plus_pct"] + m["wrong_share"] * 1.5 + (5 - score) * 8 + aging_bonus


def stale_cell(pct, hi_red=40, hi_amber=20):
    if isinstance(pct, str):
        return f'<td class="stale">{pct}</td>'
    color = "#C0504D" if pct >= hi_red else ("#D9803B" if pct >= hi_amber else "")
    style = f' style="color:{color}"' if color else ""
    return f'<td class="stale"{style}>{pct:.1f}%</td>'


def render_playbook(rows):
    # rows: list of (m, arch). Rank active by urgency; canceled to the bottom.
    active = [r for r in rows if HEALTH.get(r[0]["name"], {}).get("status") != "Canceled"]
    canceled = [r for r in rows if HEALTH.get(r[0]["name"], {}).get("status") == "Canceled"]
    active.sort(key=lambda r: urgency(r[0]), reverse=True)
    body = ""
    rank = 0
    risk_sum = risk_n = lost_sum = lost_n = stable_sum = stable_n = 0.0
    for m, arch in active + canceled:
        h = HEALTH.get(m["name"], {})
        score = h.get("score", 5)
        is_cancel = h.get("status") == "Canceled"
        rank = "—" if is_cancel else rank + 1
        u = urgency(m)
        if is_cancel:
            pill = '<span class="pill u-x">Win-back</span>'
        elif u >= 58:
            pill = '<span class="pill u-high">High</span>'
        elif u >= 30:
            pill = '<span class="pill u-med">Medium</span>'
        else:
            pill = '<span class="pill u-low">Maintain</span>'
        wrong_disp = f'{m["wrong_share"]:.1f}%' if m["wrong_count"] else "none captured"
        wrong_style = ' style="color:#C0504D"' if (m["wrong_count"] and m["wrong_share"] >= 15) else (
            ' style="color:#D9803B"' if (m["wrong_count"] and m["wrong_share"] >= 8) else "")
        # MRR at risk: canceled = already lost; health <= At Risk (3) = at risk; else stable.
        mrr = h.get("mrr") or 0
        if is_cancel:
            lost_sum += mrr; lost_n += 1
            mrr_cell = f'<td class="mrr lost">${mrr:,.0f}/mo<br><span>lost</span></td>'
        elif score <= 3:
            risk_sum += mrr; risk_n += 1
            mrr_cell = f'<td class="mrr risk">${mrr:,.0f}/mo<br><span>at risk</span></td>'
        else:
            stable_sum += mrr; stable_n += 1
            mrr_cell = f'<td class="mrr">${mrr:,.0f}/mo</td>'
        sub = f"{m['total']:,} props" + (" · Canceled" if is_cancel else "")
        body += (
            f'<tr><td class="rank">{rank}</td>'
            f'<td><b>{m["name"]}</b><br><span style="color:#999">{sub}</span></td>'
            f'<td>{h.get("csm", "—")}</td>'
            f'<td class="hs {SCORE_CLASS.get(score, "")}">{score} · {SCORE_LABEL.get(score, "?")}</td>'
            f'{mrr_cell}'
            f'{stale_cell(m["one_plus_pct"], hi_red=90, hi_amber=80)}'
            f'{stale_cell(m["two_plus_pct"])}'
            f'<td{wrong_style}>{wrong_disp}</td>'
            f'<td>{pill}</td>'
            f'<td class="talk">{talking_point(m, arch)}</td></tr>'
        )
    banner = (
        '<div class="banner">'
        f'<div class="bitem risk"><div class="bv">${risk_sum:,.0f}/mo</div>'
        f'<div class="bl">MRR at risk · {int(risk_n)} accounts (health ≤ At Risk)<br><span>≈ ${risk_sum * 12:,.0f}/yr exposed</span></div></div>'
        f'<div class="bitem lost"><div class="bv">${lost_sum:,.0f}/mo</div>'
        f'<div class="bl">Already lost · {int(lost_n)} canceled<br><span>≈ ${lost_sum * 12:,.0f}/yr · win-back</span></div></div>'
        f'<div class="bitem ok"><div class="bv">${stable_sum:,.0f}/mo</div>'
        f'<div class="bl">Stable · {int(stable_n)} healthy accounts</div></div>'
        '</div>'
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Skiptrace Refresh — Internal CSM Playbook</title>
<style>
  @page {{ size: letter landscape; margin: 0.4in; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Calibri, Arial, sans-serif; color: #2b2b2b; background: #eef2f6; padding: 24px; }}
  .wrap {{ max-width: 1150px; margin: 0 auto; background: #fff; border-radius: 10px; padding: 30px 34px; }}
  .tag {{ font-size: 12px; letter-spacing: 2px; color: #C0504D; font-weight: 700; text-transform: uppercase; }}
  h1 {{ font-size: 26px; color: #1F4E78; margin: 4px 0 2px; }}
  .sub {{ font-size: 13px; color: #888; margin-bottom: 18px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
  th {{ background: #1F4E78; color: #fff; text-align: left; padding: 9px 10px; font-weight: 600; }}
  td {{ padding: 9px 10px; border-bottom: 1px solid #eef0f2; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #f8fafc; }}
  .rank {{ font-weight: 800; color: #1F4E78; text-align: center; }}
  .pill {{ display: inline-block; padding: 2px 9px; border-radius: 11px; font-size: 11px; font-weight: 700; color: #fff; white-space: nowrap; }}
  .u-high {{ background: #C0504D; }} .u-med {{ background: #E0A93B; }} .u-low {{ background: #2E9E5B; }} .u-x {{ background: #888; }}
  .hs {{ font-weight: 700; }}
  .hs1 {{ color: #C0504D; }} .hs2 {{ color: #D9803B; }} .hs3 {{ color: #C9A227; }} .hs4 {{ color: #2E9E5B; }}
  .stale {{ font-weight: 700; }}
  .talk {{ color: #444; }}
  .legend {{ font-size: 11px; color: #777; margin-top: 14px; line-height: 1.6; }}
  .banner {{ display: flex; gap: 14px; margin: 4px 0 18px; }}
  .bitem {{ flex: 1; border-radius: 8px; padding: 12px 16px; border: 1px solid #e3e9ef; }}
  .bitem .bv {{ font-size: 22px; font-weight: 800; }}
  .bitem .bl {{ font-size: 11px; color: #666; margin-top: 3px; line-height: 1.4; }}
  .bitem .bl span {{ color: #999; }}
  .bitem.risk {{ background: #fdf3f2; border-color: #f0c4c0; }} .bitem.risk .bv {{ color: #C0504D; }}
  .bitem.lost {{ background: #f4f4f4; }} .bitem.lost .bv {{ color: #888; }}
  .bitem.ok {{ background: #f1f8f3; border-color: #cfe6d6; }} .bitem.ok .bv {{ color: #2E9E5B; }}
  .mrr {{ font-weight: 700; white-space: nowrap; }}
  .mrr.risk {{ color: #C0504D; }} .mrr.risk span {{ font-size: 10px; font-weight: 600; }}
  .mrr.lost {{ color: #999; text-decoration: line-through; }} .mrr.lost span {{ font-size: 10px; text-decoration: none; color: #aaa; }}
</style></head><body>
<div class="wrap">
  <div class="tag">Internal · Not for client distribution</div>
  <h1>Skiptrace Refresh — CSM Playbook</h1>
  <div class="sub">Who to call first, why, and the one-line talking point · Prepared {TODAY} · Blends contact-data staleness, wrong-number rate, and CS health score</div>
  {banner}
  <table>
    <thead><tr><th>#</th><th>Client</th><th>CSM</th><th>Health</th><th>MRR</th><th>1+ yr data</th><th>2+ yr data</th><th>Wrong #</th><th>Urgency</th><th>Talking point (client-safe)</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
  <div class="legend">
    <b>Health score:</b> 1 Critical · 2 Poor · 3 At Risk · 4 Healthy · 5 Thriving (8020REI AI CS score) &nbsp;|&nbsp;
    <b>1+ yr data</b> = share older than 1 year (early aging) · <b>2+ yr data</b> = share older than 2 years (connect-rate drag) &nbsp;|&nbsp;
    <b>Urgency</b> blends data staleness, wrong-number rate, and CS health (at-risk + stale = retention priority). &nbsp;|&nbsp;
    <b>MRR at risk</b> = monthly revenue of accounts at health ≤ At Risk (churn-exposed); canceled = already lost.<br>
    Each High/Medium client gets a client-facing one-page Health Card the CSM shares; this playbook stays internal.
  </div>
</div></body></html>"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    for name, rec in data.items():
        if name in EXCLUDE:
            continue
        m = metrics(name, rec)
        arch = archetype(m)
        rows.append((m, arch))
        path = os.path.join(OUT_DIR, f"{name} - Skiptrace Health Card.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render_card(m, arch))
        print(f"  card: {name:26s} [{arch}]")
    pb = os.path.join(OUT_DIR, "_CSM Playbook - Internal.html")
    with open(pb, "w", encoding="utf-8") as fh:
        fh.write(render_playbook(rows))
    print(f"\n{len(rows)} client cards + 1 playbook written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
