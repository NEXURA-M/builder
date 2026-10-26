#!/usr/bin/env python3
"""
scripts/init_domains.py
-----------------------
Regenerate domains/registry.html — the single source of truth for all TLDs.

Behaviour
=========
• If domains/registry.html already exists, every `name=path` line inside each
  `<pre class="lyra-target" data-tld="…">` block is preserved verbatim.
• New TLDs get an empty block (or the seed line if one is defined below).
• Ensures ai/, web/, game/, other/ folders exist with a .gitkeep.
• Idempotent — running it twice produces byte‑identical output.

Usage
=====
    python scripts/init_domains.py
"""

import os
import re
import sys

# ------------------------------------------------------------------ TLD table
# (tld, price_usd, note, seed_lines)
#   price_usd == 0  →  FREE (publish instantly via builder)
#   note            →  shown next to the price on registry.html
#   seed_lines      →  only used when the block is created for the first time

TLDS = [
    # ── classic paid ─────────────────────────────────────────────
    ("com",         2,   "",              ""),
    ("net",         2,   "",              ""),
    ("org",         2,   "",              ""),

    # ── pro ──────────────────────────────────────────────────────
    ("mt",          3,   "pro",           "taqi=ai/taqi.html"),
    ("zf",          3,   "pro",           ""),

    # ── student ─────────────────────────────────────────────────
    ("stu",         1,   "students",      ""),

    # ── lyra sub-TLDs ───────────────────────────────────────────
    ("lyra.com",    1,   "",              ""),
    ("lyra.net",    1,   "",              ""),
    ("lyra.org",    1,   "",              ""),
    ("lyra.mt",     2,   "",              ""),
    ("lyra.zf",     2,   "",              ""),

    # ── free tier ───────────────────────────────────────────────
    ("lyra.stu",    0,   "",              ""),
    ("taqi.lyra",   0,   "",              ""),
    ("taqi.tk",     0,   "",              ""),
    ("taqi.tl",     0,   "",              ""),
    ("lyra.tk",     0,   "",              ""),

    # ── premium ─────────────────────────────────────────────────
    ("app",         100, "",              ""),
    ("site",        100, "",              ""),
    ("lyra.app",    50,  "",              ""),
    ("lyra.site",   50,  "",              ""),

    # ── google hd pro ───────────────────────────────────────────
    ("oneapp.dev",  10,  "google hd pro", ""),
    ("duckdns.org", 10,  "google hd pro", ""),
    ("ai.studio",   20,  "",              ""),
]

# ------------------------------------------------------------------ paths

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOM  = os.path.join(ROOT, "domains")
OUT  = os.path.join(DOM, "registry.html")

CATEGORIES = ("ai", "web", "game", "other")

# ------------------------------------------------------------------ HTML head

HEAD = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lyra Domain Registry</title>
<style>
:root{--bg:#07070c;--ink:#e9e9f2;--muted:#8b8ba7;--line:#2a2a44;
--card:#0e0e18;--violet:#a78bfa;--cyan:#22d3ee;--green:#34d399}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);
  font-family:ui-monospace,Menlo,Consolas,monospace;
  padding:28px;line-height:1.6;max-width:960px;margin:0 auto}
h1{color:var(--violet);margin:0 0 6px;
  font-family:'Space Grotesk',system-ui,sans-serif;
  font-size:28px;letter-spacing:-.02em}
h2{margin:28px 0 8px;font-size:15px;color:var(--cyan);font-weight:600;
  font-family:'Space Grotesk',system-ui,sans-serif}
h2 small{color:var(--muted);font-weight:400;margin-left:8px;font-size:12px}
h2 small.free{color:var(--green)}
p{color:var(--muted);font-size:13px}
p code{color:var(--cyan);background:rgba(34,211,238,.06);
  padding:1px 6px;border-radius:4px}
.lyra-target{white-space:pre-wrap;background:var(--card);
  border:1px solid var(--line);border-radius:12px;
  padding:14px 16px;line-height:1.9;min-height:28px;margin:0;
  color:var(--ink);font-family:ui-monospace,Menlo,Consolas,monospace;
  font-size:13px;overflow-x:auto}
.lyra-target:empty::before{content:"(empty)";
  color:#4a4a66;font-style:italic}
footer{margin-top:60px;padding-top:18px;border-top:1px solid var(--line);
  color:var(--muted);font-size:12px;text-align:center}
</style></head><body>
<h1>Lyra Domain Registry</h1>
<p>Every TLD lives in this single file. Each
   <code>&lt;pre class="lyra-target" data-tld="…"&gt;</code>
   holds one <code>name=category/file.html</code> per line.</p>
'''

FOOT = '''
<footer>Lyra · created by Muhammad Taqi</footer>
</body></html>
'''

# ------------------------------------------------------------------ read existing

def read_existing(path):
    """Return {tld: inner_text} for every <pre data-tld="…"> in `path`."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        print(f"⚠️  could not read {path}: {e}")
        return {}

    pattern = re.compile(
        r'<pre\b[^>]*\bdata-tld=["\']([^"\']+)["\'][^>]*>(.*?)</pre>',
        re.DOTALL,
    )
    blocks = {}
    for m in pattern.finditer(content):
        tld   = m.group(1).strip()
        inner = m.group(2).strip()
        blocks[tld] = inner
    return blocks

# ------------------------------------------------------------------ render

def render_block(tld, price, note, inner):
    if price == 0:
        label    = "FREE"
        small    = ' class="free"'
    else:
        label = f"paid ${price}"
        small = ''
    if note:
        label += f" · {note}"

    return (
        f'<h2>.{tld} <small{small}>{label}</small></h2>\n'
        f'<pre class="lyra-target" data-tld="{tld}" '
        f'data-price="{price}">{inner}</pre>\n'
    )

# ------------------------------------------------------------------ main

def ensure_categories():
    for cat in CATEGORIES:
        path = os.path.join(ROOT, cat)
        os.makedirs(path, exist_ok=True)
        keep = os.path.join(path, ".gitkeep")
        if not os.path.exists(keep):
            open(keep, "w").close()
            print(f"   📁 created {cat}/.gitkeep")

def main():
    os.makedirs(DOM, exist_ok=True)
    print(f"📂 working dir: {ROOT}")

    existing = read_existing(OUT)
    if existing:
        print(f"♻️  preserving {sum(len(v.splitlines()) for v in existing.values() if v)} "
              f"existing entries across {len(existing)} TLD(s)")

    parts = [HEAD]
    for tld, price, note, seed in TLDS:
        inner = existing.get(tld, seed)
        parts.append(render_block(tld, price, note, inner))
    parts.append(FOOT)

    html = "\n".join(parts)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    ensure_categories()

    # ── report ────────────────────────────────────────────────────
    total_tlds    = len(TLDS)
    total_free    = sum(1 for _, p, _, _ in TLDS if p == 0)
    total_entries = 0

    print(f"\n✅ wrote {OUT}")
    print(f"   {total_tlds} TLDs ({total_free} free)\n")
    print(f"   {'TLD':<14} {'PRICE':>6}  ENTRIES  NOTE")
    print(f"   {'-'*14} {'-'*6}  -------  ----")
    for tld, price, note, seed in TLDS:
        inner = existing.get(tld, seed)
        count = len([ln for ln in inner.splitlines() if "=" in ln])
        total_entries += count
        price_s = "FREE" if price == 0 else f"${price}"
        print(f"   .{tld:<13} {price_s:>6}  {count:>7}  {note}")

    print(f"\n   total entries: {total_entries}")
    print(f"\n🎉 done. Now you can run:  python scripts/server.py")

    return 0

# ------------------------------------------------------------------ entry

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⚠️  interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ error: {e}")
        raise
