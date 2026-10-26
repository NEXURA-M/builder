import os, re, base64
from flask import Flask, request, jsonify, send_from_directory
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, static_folder=None)

FREE_TLDS  = {'lyra.stu', 'taqi.lyra', 'taqi.tk', 'taqi.tl', 'lyra.tk'}
CATEGORIES = {'ai', 'web', 'game', 'other'}

GITHUB_TOKEN  = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO   = os.environ.get('GITHUB_REPOSITORY', '')
GITHUB_BRANCH = os.environ.get('GITHUB_REF_NAME', 'main')


def pages_url():
    url = os.environ.get('PAGES_URL', '').strip()
    if url:
        return url.rstrip('/')
    if GITHUB_REPO:
        owner, name = GITHUB_REPO.split('/', 1)
        if name.lower() == f'{owner.lower()}.github.io':
            return f'https://{owner.lower()}.github.io'
        return f'https://{owner.lower()}.github.io/{name}'
    return ''


def gh_headers():
    return {'Authorization': f'Bearer {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github+json'}


def gh_get(path):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
    r = requests.get(url, headers=gh_headers(),
                     params={'ref': GITHUB_BRANCH}, timeout=20)
    if r.status_code == 200:
        return base64.b64decode(r.json()['content']).decode('utf-8')
    return None


def gh_put(path, text, message):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, 'no github credentials'
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
    r = requests.get(url, headers=gh_headers(),
                     params={'ref': GITHUB_BRANCH}, timeout=20)
    sha = r.json().get('sha') if r.status_code == 200 else None
    body = {'message': message,
            'content': base64.b64encode(text.encode('utf-8')).decode('ascii'),
            'branch': GITHUB_BRANCH}
    if sha:
        body['sha'] = sha
    r = requests.put(url, headers=gh_headers(), json=body, timeout=20)
    return (r.status_code in (200, 201)), r.text[:300]


def domain_template(tld):
    return f'''<!doctype html>
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
</body></html>'''


# ---------- routes ----------
@app.route('/')
def home():
    return send_from_directory(ROOT, 'builder.html')


@app.route('/api/config')
def config():
    return jsonify(pages_url=pages_url(), free_tlds=sorted(FREE_TLDS))


@app.route('/api/submit', methods=['POST'])
def submit():
    data     = request.get_json(force=True) or {}
    category = (data.get('category') or '').lower()
    name     = (data.get('name') or '').strip()
    html     = data.get('html') or ''
    tld      = (data.get('tld') or '').strip().lower()

    if category not in CATEGORIES:
        return jsonify(ok=False, error='invalid category'), 400
    if not re.match(r'^[a-zA-Z0-9_-]{2,32}$', name):
        return jsonify(ok=False, error='invalid name (2-32 letters/numbers/dashes)'), 400
    if len(html) < 50:
        return jsonify(ok=False, error='html too short'), 400
    if tld not in FREE_TLDS:
        return jsonify(ok=False, error='paid',
                       contact='https://mustjab-king-lyra.hf.space/'), 402

    slug = name.lower()
    path = f'{category}/{slug}.html'

    if gh_get(path) is not None:
        return jsonify(ok=False, error=f'{slug}.{tld} already taken'), 409

    ok, msg = gh_put(path, html, f'Add {slug}.{tld} · Lyra Builder')
    if not ok:
        return jsonify(ok=False, error='commit failed: ' + msg), 500

    dpath = f'domains/{tld}.html'
    dfile = gh_get(dpath) or domain_template(tld)
    line  = f'{slug}={category}/{slug}.html'
    if line not in dfile:
        if '</pre>' in dfile:
            dfile = dfile.replace('</pre>', f'\n{line}\n</pre>', 1)
        else:
            dfile += f'\n<pre class="lyra-target">{line}</pre>'
        ok2, msg2 = gh_put(dpath, dfile, f'Map {slug}.{tld}')
        if not ok2:
            return jsonify(ok=False, error='domain map failed: ' + msg2), 500

    base = pages_url()
    return jsonify(ok=True,
                   virtual=f'{slug}.{tld}',
                   live=f'{base}/{path}',
                   browser=f'{base}/index.html#{slug}.{tld}')


@app.route('/<path:path>')
def static_any(path):
    return send_from_directory(ROOT, path)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, threaded=True)
