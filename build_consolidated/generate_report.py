"""Generate the consolidated 11-client Skiptrace Data-Age Diagnosis.

Emits two self-contained HTML files (8020REI design system, print-ready):
  Reports/Consolidated/Consolidated Skiptrace Diagnosis - Internal.html
  Reports/Consolidated/Consolidated Skiptrace Diagnosis - Client.html

Internal  = full picture incl. source tiers (T1/T2/...) + ops findings.
Client    = age-only, no source tiers, no internal sourcing/ops narrative.
"""
import json, base64, os, datetime

ROOT = "F:/8020/Skiptrace-Age-Project"
LOGO_DIR = f"{ROOT}/8020REI-skills-main/8020REI-skills-main/customer_success/logos"
OUT_DIR = f"{ROOT}/Reports/Consolidated"
os.makedirs(OUT_DIR, exist_ok=True)

data = json.load(open(f"{ROOT}/build_consolidated/data.json"))
# Excluded portfolios (too small to be worth diagnosing in the consolidated view).
EXCLUDE = {"Atlas Residential"}
data = {c: r for c, r in data.items() if c not in EXCLUDE}
TODAY = datetime.date.today()
DATE_LABEL = TODAY.strftime("%B %Y")

AGE = ["<1 year", "1-2 years", "2+ years"]
TIERS = ["T1", "T2", "T3", "T6", "T8", "Others", "Unknown"]
# Age colors: semantic risk gradient (fresh -> stale). Always paired with labels.
AGE_COLOR = {"<1 year": "#166534", "1-2 years": "#B45309", "2+ years": "#991B1B"}

def b64(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

LOGO_FULL = b64(f"{LOGO_DIR}/logo-full-light.png")
LOGO_ICON = b64(f"{LOGO_DIR}/logo-icon-light.png")

# ---------- aggregates ----------
def cdata(c):
    return data[c]

tot = sum(r["total"] for r in data.values())
NC = len(data)                          # client count (after exclusions)
TOTM = f"{tot / 1_000_000:.2f}M"        # e.g. "3.10M"
age = {k: sum(r["age_dist"].get(k, 0) for r in data.values()) for k in AGE}
one_plus = age["1-2 years"] + age["2+ years"]

logged = {c: r for c, r in data.items() if r["wrong_count"]}
not_logged = [c for c, r in data.items() if not r["wrong_count"]]
wn_tot = sum(r["wrong_count"] for r in logged.values())
wn_base = sum(r["total"] for r in logged.values())
wn_age = {k: sum(r["wrong_age_dist"].get(k, 0) for r in logged.values()) for k in AGE}
untracked_props = sum(data[c]["total"] for c in not_logged)

src = {t: {k: 0 for k in AGE + ["Total"]} for t in TIERS}
for r in data.values():
    for s, vals in (r.get("source_full") or {}).items():
        b = s if s in TIERS else "Unknown"
        for k in AGE + ["Total"]:
            src[b][k] += vals.get(k) or 0

# ---------- formatting helpers ----------
def n(x):
    return f"{int(x):,}"

def pct(part, whole, dp=1):
    return f"{(part / whole * 100):.{dp}f}%" if whole else "0%"

def client_2plus(c):
    return data[c]["age_dist"].get("2+ years", 0)

def client_1plus(c):
    a = data[c]["age_dist"]
    return a.get("1-2 years", 0) + a.get("2+ years", 0)

# stacked horizontal bar from three age counts
def age_bar(counts, total, height=13, show_legend=False):
    if not total:
        return ""
    segs = ""
    for k in AGE:
        v = counts.get(k, 0)
        if v <= 0:
            continue
        w = v / total * 100
        segs += (f'<div style="width:{w:.3f}%;background:{AGE_COLOR[k]};height:100%;" '
                 f'title="{k}: {n(v)}"></div>')
    return (f'<div style="display:flex;width:100%;height:{height}px;'
            f'border:1px solid #d4d4d4;overflow:hidden;">{segs}</div>')

def legend():
    items = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;margin-right:20px;">'
        f'<span style="width:11px;height:11px;background:{AGE_COLOR[k]};display:inline-block;"></span>'
        f'<span style="font-size:11px;color:#2d2d2d;">{k}</span></span>'
        for k in AGE)
    return f'<div style="margin:10px 0 16px;">{items}</div>'

# ---------- shared CSS (8020REI design system, from the canonical example) ----------
CSS = """
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}
html{font-size:16px;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
body{font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;color:#1a1a1a;background:#ffffff;line-height:1.6;}
h1,h2,h3{font-family:Georgia,'Times New Roman',serif;font-weight:700;color:#1a1a1a;line-height:1.2;}
h1{font-size:2.25rem;letter-spacing:-0.02em;}
h2{font-size:1.5rem;letter-spacing:-0.01em;}
h3{font-size:1.125rem;}
p,li,td,th{font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:0.9375rem;color:#1a1a1a;line-height:1.6;}
.page{width:8.5in;min-height:11in;max-height:11in;margin:0 auto;padding:44px 56px 64px;page-break-after:always;position:relative;background:#fff;overflow:hidden;page-break-inside:avoid;}
.page:last-child{page-break-after:auto;}
@media screen{.page{border:1px solid #d4d4d4;margin-bottom:24px;}}
.section-label{font-size:0.6875rem;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#0B5394;margin-bottom:8px;display:block;}
.action-title{font-family:Georgia,'Times New Roman',serif;font-size:1.25rem;font-weight:700;color:#1a1a1a;line-height:1.35;margin-bottom:24px;border-bottom:2px solid #0B5394;padding-bottom:12px;}
.action-title .highlight{color:#0B5394;}
.kpi-row{display:flex;gap:0;margin-bottom:26px;}
.kpi-card{flex:1;padding:16px 18px;border:1px solid #d4d4d4;border-right:none;text-align:center;}
.kpi-card:last-child{border-right:1px solid #d4d4d4;}
.kpi-label{font-size:0.625rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#666;margin-bottom:6px;}
.kpi-value{font-family:Georgia,'Times New Roman',serif;font-size:1.85rem;font-weight:700;color:#0B5394;line-height:1.1;}
.kpi-context{font-size:0.7rem;color:#666;margin-top:4px;}
.insight-box{background:#E8F0FE;border-left:3px solid #0B5394;padding:14px 18px;margin-bottom:22px;}
.insight-box p{font-size:0.85rem;line-height:1.55;}
.insight-box.warn{border-left-color:#B45309;background:#FEF3C7;}
.insight-box.negative{border-left-color:#991B1B;background:#FEE2E2;}
.insight-box.positive{border-left-color:#166534;background:#DCFCE7;}
.sub-section-header{font-family:Georgia,'Times New Roman',serif;font-size:1rem;font-weight:700;color:#1a1a1a;margin-top:6px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #d4d4d4;}
.two-col{display:flex;gap:32px;margin-bottom:24px;}
.two-col .col{flex:1;}
table{width:100%;border-collapse:collapse;margin-bottom:14px;}
th{font-size:0.625rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#666;text-align:left;padding:7px 8px 7px 0;border-bottom:2px solid #1a1a1a;}
td{font-size:0.8rem;padding:6px 8px 6px 0;border-bottom:1px solid #ebebeb;color:#2d2d2d;vertical-align:middle;}
tr:last-child td{border-bottom:none;}
.num{text-align:right;font-variant-numeric:tabular-nums;}
.tfoot td{font-weight:700;color:#1a1a1a;border-top:2px solid #1a1a1a;border-bottom:none;}
ul.bullet-list{list-style:none;padding:0;margin-bottom:14px;}
ul.bullet-list li{font-size:0.875rem;line-height:1.5;color:#2d2d2d;padding-left:16px;position:relative;margin-bottom:8px;}
ul.bullet-list li::before{content:'';position:absolute;left:0;top:8px;width:5px;height:5px;background:#0B5394;border-radius:50%;}
ul.bullet-list li strong{color:#1a1a1a;}
ol.step-list{list-style:none;counter-reset:step;padding:0;margin-bottom:14px;}
ol.step-list li{counter-increment:step;display:flex;gap:12px;align-items:flex-start;margin-bottom:11px;font-size:0.85rem;color:#2d2d2d;line-height:1.5;}
ol.step-list li::before{content:counter(step);font-family:Georgia,serif;min-width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#0B5394;border:1.5px solid #0B5394;border-radius:50%;flex-shrink:0;}
.cover{display:flex;flex-direction:column;justify-content:center;}
.cover-logo{margin-bottom:56px;}
.cover-logo img{height:52px;display:block;}
.cover-divider{width:64px;height:3px;background:#0B5394;margin-bottom:30px;}
.cover-title{font-family:Georgia,serif;font-size:2.3rem;font-weight:700;color:#1a1a1a;line-height:1.18;margin-bottom:18px;letter-spacing:-0.02em;}
.cover-subtitle{font-size:1.0625rem;color:#666;margin-bottom:44px;line-height:1.5;}
.cover-confidential{font-size:0.6875rem;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#999;border-top:1px solid #d4d4d4;padding-top:16px;display:inline-block;}
.page-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px;padding-bottom:10px;border-bottom:1px solid #d4d4d4;}
.page-header img{height:20px;}
.page-header span{font-size:0.75rem;color:#999;}
.page-footer{position:absolute;bottom:30px;left:56px;right:56px;display:flex;justify-content:space-between;align-items:center;font-size:0.625rem;color:#999;letter-spacing:0.05em;border-top:1px solid #d4d4d4;padding-top:10px;}
.page-footer a{color:#999;text-decoration:none;}
.page-footer a:hover{text-decoration:underline;}
.download-btn{position:fixed;top:20px;right:20px;z-index:1000;padding:10px 20px;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:0.8rem;font-weight:600;color:#fff;background:#0B5394;border:none;cursor:pointer;letter-spacing:0.05em;}
.download-btn:hover{background:#094075;}
@page{margin:0;size:8.5in 11in;}
@media print{body{background:none;}.page{width:8.5in;height:11in;margin:0;padding:44px 56px 64px;border:none;}.page-footer{position:fixed;bottom:24px;}.download-btn{display:none;}}
"""

def header(date=DATE_LABEL):
    return (f'<div class="page-header"><img src="{LOGO_ICON}" alt="8020REI">'
            f'<span>{date}</span></div>')

def footer(pn):
    return ('<footer class="page-footer">'
            '<span><a href="https://booking.8020rei.com">8020rei.com</a></span>'
            '<span>Confidential</span>'
            f'<span>Page {pn}</span></footer>')

def cover(title, subtitle):
    return f"""
<section class="page cover">
  <div class="cover-logo"><img src="{LOGO_FULL}" alt="8020REI"></div>
  <div class="cover-divider"></div>
  <h1 class="cover-title">{title}</h1>
  <p class="cover-subtitle">{subtitle}</p>
  <div class="cover-confidential">Confidential</div>
  {footer(1)}
</section>"""

def kpi(label, value, ctx, color=None):
    style = f' style="color:{color};"' if color else ""
    return (f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value"{style}>{value}</div>'
            f'<div class="kpi-context">{ctx}</div></div>')

# ===================================================================
#  PER-CLIENT AGE TABLE (shared by both versions)
# ===================================================================
def client_1plus_share(c):
    t = data[c]["total"]
    return client_1plus(c) / t if t else 0

def client_age_table():
    rows = ""
    # Stalest portfolios first (highest share of 1+ year data), freshest last.
    for c, r in sorted(data.items(), key=lambda x: -client_1plus_share(x[0])):
        a = r["age_dist"]; t = r["total"]
        rows += (f"<tr><td>{c}</td><td class='num'>{n(t)}</td>"
                 f"<td style='width:180px;padding-right:0;'>{age_bar(a, t, 12)}</td>"
                 f"<td class='num'>{pct(client_1plus(c), t)}</td>"
                 f"<td class='num'>{pct(a.get('2+ years',0), t)}</td></tr>")
    rows += (f"<tr class='tfoot'><td>All {NC} clients</td><td class='num'>{n(tot)}</td>"
             f"<td style='padding-right:0;'>{age_bar(age, tot, 12)}</td>"
             f"<td class='num'>{pct(one_plus, tot)}</td>"
             f"<td class='num'>{pct(age['2+ years'], tot)}</td></tr>")
    return (f"<table><thead><tr><th>Client portfolio</th><th class='num'>Properties</th>"
            f"<th>Data-age mix</th><th class='num'>1+ yr</th><th class='num'>2+ yr</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>")

# ===================================================================
#  INTERNAL REPORT
# ===================================================================
def build_internal():
    t1 = src["T1"]; t2 = src["T2"]
    fresh = src["T3"]["Total"] + src["T6"]["Total"] + src["T8"]["Total"]
    t1_1plus = t1["1-2 years"] + t1["2+ years"]
    old2 = age["2+ years"]
    t1t2_2plus = t1["2+ years"] + t2["2+ years"]

    # --- page 2: scale & age ---
    p2 = f"""
<section class="page">
  {header()}
  <span class="section-label">Portfolio Scale &amp; Data Age</span>
  <div class="action-title">Across the {NC} diagnosed portfolios, <span class="highlight">{pct(one_plus,tot,0)} of {TOTM} skiptraced records are 1+ years old</span> and more than a third are 2+ years old &mdash; the cohort most exposed to stale phone numbers.</div>
  <div class="kpi-row">
    {kpi("Properties Diagnosed", TOTM, f"{NC} client portfolios")}
    {kpi("Data 1+ Years Old", pct(one_plus,tot,0), f"{n(one_plus)} records")}
    {kpi("Data 2+ Years Old", pct(age['2+ years'],tot,0), f"{n(age['2+ years'])} records", "#991B1B")}
    {kpi("Data Under 1 Year", pct(age['<1 year'],tot,0), f"{n(age['<1 year'])} records", "#166534")}
  </div>
  {legend()}
  {client_age_table()}
  <div class="insight-box warn">
    <p><strong>Why age is the right lever: contactability decays fast.</strong> The FCC estimates ~35M U.S. numbers are disconnected and reassigned each year (~10% of all numbers), and ~42.9% of people change phone number within 12 months &mdash; so by 1&ndash;2 years a record is materially less likely to reach the intended person, and by 2+ years many numbers are dead. That decay, not any status flag, is the case for refreshing the oldest records first.
    <span style="display:block;font-size:0.7rem;color:#666;margin-top:6px;">Sources: FCC, <em>Reassigned Numbers Database</em>; IndustrySelect, &ldquo;The High Cost of Bad Contact Data.&rdquo;</span></p>
  </div>
  {footer(2)}
</section>"""

    # --- page 3: source ---
    def srow(t):
        v = src[t]
        return (f"<tr><td>{t}</td><td class='num'>{n(v['Total'])}</td>"
                f"<td class='num'>{pct(v['Total'],tot)}</td>"
                f"<td class='num'>{n(v['<1 year'])}</td>"
                f"<td class='num'>{n(v['1-2 years'])}</td>"
                f"<td class='num'>{n(v['2+ years'])}</td>"
                f"<td style='width:120px;padding-right:0;'>{age_bar(v,v['Total'],11)}</td></tr>")
    src_rows = "".join(srow(t) for t in sorted(TIERS, key=lambda x:-src[x]["Total"]) if src[t]["Total"])
    src_rows += (f"<tr class='tfoot'><td>Total</td><td class='num'>{n(tot)}</td><td class='num'>100%</td>"
                 f"<td class='num'>{n(age['<1 year'])}</td><td class='num'>{n(age['1-2 years'])}</td>"
                 f"<td class='num'>{n(age['2+ years'])}</td><td style='padding-right:0;'>{age_bar(age,tot,11)}</td></tr>")
    p3 = f"""
<section class="page">
  {header()}
  <span class="section-label">Source &times; Age</span>
  <div class="action-title">The aging lives in <span class="highlight">legacy T1 sourcing</span>. T1 is the largest tier &mdash; {pct(t1['Total'],tot,0)} of all records &mdash; and the oldest: {pct(t1_1plus,t1['Total'],0)} of it is already 1+ years old. The newer tiers (T3, T6, T8) are almost all under a year.</div>
  {legend()}
  <table>
    <thead><tr><th>Source tier</th><th class='num'>Properties</th><th class='num'>% book</th>
    <th class='num'>&lt;1 yr</th><th class='num'>1-2 yr</th><th class='num'>2+ yr</th><th>Age mix</th></tr></thead>
    <tbody>{src_rows}</tbody>
  </table>
  <div class="insight-box">
    <p><strong>T1, T2 and Unknown carry virtually all the stale data.</strong> Of the {n(old2)} records that are 2+ years old, {pct(t1t2_2plus+src['Unknown']['2+ years'],old2,0)} sit in T1, T2, or Unknown. The 2026 tiers (T3, T6, T8 &mdash; {n(fresh)} records combined) are ~100% under one year, confirming they came from recent pulls and are the higher-intent cohort for active dialing.</p>
  </div>
  <div class="insight-box warn">
    <p><strong>Tagging hygiene is a real gap: {n(src['Unknown']['Total'])} records ({pct(src['Unknown']['Total'],tot,0)}) have no identifiable source tier.</strong> One in seven records can't be attributed to a sourcing batch, which limits how precisely we can target refresh spend. Worth tightening SOURCE/TAGS capture at intake.</p>
  </div>
  {footer(3)}
</section>"""

    # --- page 4: wrong numbers ---
    def wrow(c):
        r = data[c]; wc = r["wrong_count"]
        return (f"<tr><td>{c}</td><td class='num'>{n(wc)}</td>"
                f"<td class='num'>{n(r['total'])}</td>"
                f"<td class='num'>{r['wrong_share_pct']}%</td></tr>")
    w_rows = "".join(wrow(c) for c,_ in sorted(logged.items(), key=lambda x:-x[1]["wrong_share_pct"]))
    p4 = f"""
<section class="page">
  {header()}
  <span class="section-label">Wrong Numbers &amp; Tracking Gaps</span>
  <div class="action-title">Across the portfolios that track outcomes, <span class="highlight">{pct(wn_tot,wn_base)} of properties carry a wrong number</span> &mdash; a useful intake-quality signal that shows where call lists need attention. Enabling the same tracking on the two largest books is an easy next win.</div>
  <div class="kpi-row">
    {kpi("Wrong Numbers", n(wn_tot), f"of {n(wn_base)} tracked")}
    {kpi("Avg Wrong Rate", pct(wn_tot,wn_base), "where STATUS is logged")}
    {kpi("Books Tracking", f"{len(logged)} of {NC}", "STATUS captured")}
    {kpi("Untracked Volume", n(untracked_props), "Patriot + Rapid Fire", "#991B1B")}
  </div>
  <table>
    <thead><tr><th>Client portfolio</th><th class='num'>Wrong #s</th><th class='num'>Properties</th><th class='num'>Rate</th></tr></thead>
    <tbody>{w_rows}</tbody>
  </table>
  <div class="insight-box">
    <p><strong>Read this as a data-quality signal, not an age signal.</strong> Because a number&rsquo;s <em>NUMBER CREATED AT</em> updates each time it&rsquo;s refreshed or returned through the domain, the recorded date reflects the latest pull rather than the original skiptrace &mdash; so age isn&rsquo;t the right lens for wrong numbers. What the rate <em>does</em> show is where call lists degrade fastest &mdash; Leave the Key ({round(data['Leave the Key']['wrong_share_pct'])}%), Pillar ({round(data['Pillar Home Buyers']['wrong_share_pct'])}%) and Cava ({round(data['Cava']['wrong_share_pct'])}%) lead &mdash; warranting a source-quality review at intake. The case for refreshing aged records rests on industry contactability decay (prior page), a lever separate from this rate.</p>
  </div>
  <div class="insight-box warn">
    <p><strong>Blind spot: Patriot Home Buyers and Rapid Fire HB ({n(untracked_props)} properties, {pct(untracked_props,tot,0)} of the book) log no wrong-number STATUS.</strong> We can't quantify their caller-productivity drag until STATUS capture is enabled in the dialer.</p>
  </div>
  {footer(4)}
</section>"""

    # --- page 5: recommendation ---
    pri = sorted(data.items(), key=lambda x:-client_2plus(x[0]))[:6]
    pri_rows = "".join(
        f"<tr><td>{i+1}</td><td>{c}</td><td class='num'>{n(client_2plus(c))}</td>"
        f"<td class='num'>{pct(client_2plus(c),data[c]['total'])}</td></tr>"
        for i,(c,_) in enumerate(pri))
    p5 = f"""
<section class="page">
  {header()}
  <span class="section-label">Recommendation &amp; Next Steps</span>
  <div class="action-title">Run a <span class="highlight">prioritized re-skiptrace of the oldest T1/T2 cohorts</span>, starting with the six books that hold the most 2+ year data, and close the tagging and STATUS-capture gaps in parallel.</div>
  <div class="two-col">
    <div class="col">
      <h3 class="sub-section-header">Why this, in order</h3>
      <ol class="step-list">
        <li><strong>Refresh oldest-first.</strong> {n(age['2+ years'])} records are 2+ years old and overwhelmingly T1/T2 &mdash; the largest, stalest, highest-recovery cohort.</li>
        <li><strong>Review source quality where wrong-number rates run high.</strong> Leave the Key, Pillar and Cava carry the highest wrong-number rates &mdash; a source-quality review at intake will do more there than a re-skiptrace alone.</li>
        <li><strong>Turn on STATUS capture</strong> for Patriot and Rapid Fire so the {pct(untracked_props,tot,0)} of the book we're blind to becomes measurable.</li>
        <li><strong>Fix tagging at intake</strong> to shrink the {pct(src['Unknown']['Total'],tot,0)} Unknown-source cohort and sharpen future targeting.</li>
      </ol>
    </div>
    <div class="col">
      <h3 class="sub-section-header">Re-skiptrace priority (by 2+ yr volume)</h3>
      <table>
        <thead><tr><th>#</th><th>Client</th><th class='num'>2+ yr records</th><th class='num'>% of book</th></tr></thead>
        <tbody>{pri_rows}</tbody>
      </table>
    </div>
  </div>
  <h3 class="sub-section-header">Next steps</h3>
  <table>
    <thead><tr><th>Action</th><th>Owner</th><th>Target</th></tr></thead>
    <tbody>
      <tr><td>Communicate the data-age findings to each client portfolio</td><td>Customer Success</td><td>Jun 13, 2026</td></tr>
      <tr><td>Offer a re-skiptrace plan for each client&rsquo;s stalled (1+ yr) properties</td><td>CS + Data Ops</td><td>Jun 30, 2026</td></tr>
      <tr><td>After refreshed numbers are dialed, review logged-call outcomes to measure the quality lift</td><td>CS + Data Ops</td><td>Aug 15, 2026</td></tr>
      <tr><td>Define a standard so SOURCE/TAGS are always captured at import</td><td>Data Ops</td><td>Aug 31, 2026</td></tr>
    </tbody>
  </table>
  <div class="insight-box">
    <p><strong>Expected payoff:</strong> recovering even 20% of the {n(age['2+ years'])} stale records returns ~{n(age['2+ years']*0.2)} fresh contacts to the dialers, concentrated in the four largest accounts where connect-rate lift is most visible.</p>
  </div>
  {footer(5)}
</section>"""

    title = (f"{pct(one_plus,tot,0)} of {TOTM} skiptraced records across {NC} client portfolios "
             f"are already 1+ years old &mdash; and a third are 2+ years stale. A prioritized "
             f"re-skiptrace of the oldest T1/T2 cohorts is the highest-leverage move.")
    sub = f"Consolidated Skiptrace Data-Age Diagnosis &middot; {NC} client portfolios &middot; {DATE_LABEL} &middot; Internal"
    body = cover(title, sub) + p2 + p3 + p4 + p5
    return wrap(body, "Consolidated Skiptrace Diagnosis (Internal) — 8020REI")

# ===================================================================
#  CLIENT / EXTERNAL REPORT  (age only, no source tiers, no ops critique)
# ===================================================================
def build_client():
    # page 2: scale & age
    p2 = f"""
<section class="page">
  {header()}
  <span class="section-label">Portfolio Scale &amp; Data Age</span>
  <div class="action-title">Across the {NC} portfolios reviewed, <span class="highlight">{pct(one_plus,tot,0)} of {TOTM} contact records are 1+ years old</span> and more than a third are 2+ years old &mdash; the records most likely to drag connect rates.</div>
  <div class="kpi-row">
    {kpi("Properties Reviewed", TOTM, f"{NC} portfolios")}
    {kpi("Data 1+ Years Old", pct(one_plus,tot,0), f"{n(one_plus)} records")}
    {kpi("Data 2+ Years Old", pct(age['2+ years'],tot,0), f"{n(age['2+ years'])} records", "#991B1B")}
    {kpi("Data Under 1 Year", pct(age['<1 year'],tot,0), f"{n(age['<1 year'])} records", "#166534")}
  </div>
  {legend()}
  {client_age_table()}
  <div class="insight-box warn">
    <p><strong>Why data age matters: contactability decays quickly.</strong> The FCC estimates ~35M U.S. numbers are disconnected and reassigned each year (~10% of all numbers), and ~42.9% of people change phone number within 12 months &mdash; so by 1&ndash;2 years a record is meaningfully less likely to reach the intended person, and by 2+ years many no longer connect. Refreshing the oldest records first is the clearest lever on connect rates.
    <span style="display:block;font-size:0.7rem;color:#666;margin-top:6px;">Sources: FCC, <em>Reassigned Numbers Database</em>; IndustrySelect, &ldquo;The High Cost of Bad Contact Data.&rdquo;</span></p>
  </div>
  {footer(2)}
</section>"""

    # page 3: wrong numbers (age framing only)
    def wrow(c):
        r = data[c]; wc = r["wrong_count"]
        return (f"<tr><td>{c}</td><td class='num'>{n(wc)}</td>"
                f"<td class='num'>{n(r['total'])}</td>"
                f"<td class='num'>{r['wrong_share_pct']}%</td></tr>")
    w_rows = "".join(wrow(c) for c,_ in sorted(logged.items(), key=lambda x:-x[1]["wrong_share_pct"]))
    p3 = f"""
<section class="page">
  {header()}
  <span class="section-label">Wrong-Number Cohort</span>
  <div class="action-title">Across the portfolios that track outcomes, <span class="highlight">{n(wn_tot)} properties carry a wrong number</span>. The rate ranges widely &mdash; from under 1% to about 20% &mdash; flagging where call-list quality needs the most attention.</div>
  <table>
    <thead><tr><th>Portfolio</th><th class='num'>Wrong #s</th><th class='num'>Properties</th><th class='num'>Share of portfolio</th></tr></thead>
    <tbody>{w_rows}</tbody>
  </table>
  <div class="insight-box">
    <p><strong>Wrong-number rate flags where call lists need attention.</strong> A few portfolios stand out &mdash; Leave the Key (~{round(data['Leave the Key']['wrong_share_pct'])}%), Pillar (~{round(data['Pillar Home Buyers']['wrong_share_pct'])}%) and Cava (~{round(data['Cava']['wrong_share_pct'])}%) &mdash; while most others sit under 3%. A high wrong-number rate is where a fresh skiptrace and a closer look at the originating data will recover the most usable contacts. (Two large portfolios don&rsquo;t yet log wrong-number outcomes, so their rates aren&rsquo;t shown.)</p>
  </div>
  {footer(3)}
</section>"""

    # page 4: recommendation
    p4 = f"""
<section class="page">
  {header()}
  <span class="section-label">Recommendation &amp; Next Steps</span>
  <div class="action-title">Establish a <span class="highlight">rolling refresh of the oldest records</span> &mdash; prioritizing the most-aged portfolios first &mdash; to keep the age profile weighted toward fresher, higher-yield contacts.</div>
  <ul class="bullet-list">
    <li><strong>Refresh oldest-first.</strong> The {n(age['2+ years'])} records that are 2+ years old ({pct(age['2+ years'],tot,0)} of the total) are the cohort most likely to yield recovered contacts from a fresh pull.</li>
    <li><strong>Protect caller productivity.</strong> Exclude known wrong-number properties from active queues, refresh the aged portion, and recycle returned numbers into the dialer.</li>
    <li><strong>Prioritize the heaviest books.</strong> A handful of portfolios hold the bulk of the aged data &mdash; sequencing those first delivers the most visible connect-rate lift.</li>
  </ul>
  <h3 class="sub-section-header">Suggested next steps</h3>
  <table>
    <thead><tr><th>Action</th><th>Owner</th><th>Target</th></tr></thead>
    <tbody>
      <tr><td>Review the data-age findings together for your portfolio</td><td>8020REI &amp; client team</td><td>Jun 2026</td></tr>
      <tr><td>Agree a re-skiptrace plan for the stalled (1+ yr) properties</td><td>8020REI &amp; client team</td><td>Jun 2026</td></tr>
      <tr><td>Dial the refreshed numbers; review logged calls to confirm the lift</td><td>Client calling team</td><td>Aug 2026</td></tr>
      <tr><td>Set data-capture standards to keep records fresh and attributable</td><td>8020REI Customer Success</td><td>Aug 2026</td></tr>
    </tbody>
  </table>
  <div class="insight-box">
    <p><strong>Expected payoff:</strong> refreshing the most-aged records returns fresher, more reachable contacts to the calling teams &mdash; concentrated in the portfolios where the aging is heaviest and the upside is largest.</p>
  </div>
  {footer(4)}
</section>"""

    title = (f"{pct(one_plus,tot,0)} of {TOTM} contact records across {NC} portfolios "
             f"are 1+ years old &mdash; and a third are 2+ years stale. Refreshing the oldest "
             f"records first is the clearest path to higher connect rates.")
    sub = f"Consolidated Skiptrace Data-Age Diagnosis &middot; {NC} portfolios &middot; {DATE_LABEL}"
    body = cover(title, sub) + p2 + p3 + p4
    return wrap(body, "Consolidated Skiptrace Diagnosis — 8020REI")

def wrap(body, title):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title><style>{CSS}</style></head>
<body>
<button class="download-btn" onclick="window.print()">&#8595; Download PDF</button>
{body}
</body></html>"""

with open(f"{OUT_DIR}/Consolidated Skiptrace Diagnosis - Internal.html", "w", encoding="utf-8") as f:
    f.write(build_internal())
with open(f"{OUT_DIR}/Consolidated Skiptrace Diagnosis - Client.html", "w", encoding="utf-8") as f:
    f.write(build_client())
print("Wrote 2 reports to", OUT_DIR)
