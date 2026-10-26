import os, json

TLDS = ["com","net","org","mt","zf","stu",
        "lyra.com","lyra.net","lyra.org","lyra.mt","lyra.zf","lyra.stu",
        "taqi.lyra","taqi.tk","taqi.tl","lyra.tk",
        "app","site","lyra.app","lyra.site",
        "oneapp.dev","duckdns.org","ai.studio"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOM  = os.path.join(ROOT, 'domains')
os.makedirs(DOM, exist_ok=True)

TPL = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>.{tld} · Lyra Registry</title>
<style>
body{{background:#07070c;color:#e9e9f2;font-family:ui-monospace,monospace;padding:28px}}
h1{{color:#a78bfa}} code{{color:#22d3ee}}
.lyra-target{{white-space:pre-wrap;background:#0e0e18;border:1px solid #2a2a44;
  border-radius:12px;padding:16px;line-height:1.9}}
</style></head><body>
<h1>.{tld} · Lyra Domain Registry</h1>
<p>Format: <code>name=category/file.html</code></p>
<pre class="lyra-target"></pre>
</body></html>
'''

for tld in TLDS:
    fp = os.path.join(DOM, f'{tld}.html')
    if not os.path.exists(fp):
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(TPL.format(tld=tld))
        print('created', fp)

with open(os.path.join(DOM, 'manifest.json'), 'w', encoding='utf-8') as f:
    json.dump({'tlds': TLDS}, f, indent=2)
print('manifest written')
