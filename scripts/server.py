#!/usr/bin/env python3
"""
Lyra Builder backend.

Serves builder.html on / and handles /api/submit + /api/config.
Publishes user sites to the GitHub repo and appends an entry to
domains/registry.html inside the correct <pre data-tld="…"> block.

Environment (set by GitHub Actions):
  GITHUB_TOKEN      – auto-provided by Actions
  GITHUB_REPOSITORY – "owner/repo"
  GITHUB_REF_NAME   – "main"
  PAGES_URL         – optional, e.g. https://owner.github.io/repo
"""

import os
import re
import sys
import base64
import traceback

from flask import Flask, request, jsonify, send_from_directory
import requests

# ---------------------------------------------------------------- config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, static_folder=None)

FREE_TLDS  = {'lyra.stu', 'taqi.lyra', 'taqi.tk', 'taqi.tl', 'lyra.tk'}
CATEGORIES = {'ai', 'web', 'game', 'other'}
REGISTRY   = 'domains/registry.html'          # ← single file

GITHUB_TOKEN  = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO   = os.environ.get('GITHUB_REPOSITORY', '')
GITHUB_BRANCH = os.environ.get('GITHUB_REF_NAME', 'main')

# ---------------------------------------------------------------- helpers

def pages_url():
    url = os.environ.get('PAGES_URL', '').strip()
    if url:
        return url.rstrip('/')
    if GITHUB_REPO and '/' in GITHUB_REPO:
        owner, name = GITHUB_REPO.split('/', 1)
        if name.lower() == f'{owner.lower()}.github.io':
            return f'https://{owner.lower()}.github.io'
        return f'https://{owner.lower()}.github.io/{name}'
    return ''

def gh_headers():
    return {
        'Authorization': f'Bearer {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'lyra-builder',
    }

def gh_get(path):
    """Return file content as text, or None if 404 / no creds."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
    try:
        r = requests.get(url, headers=gh_headers(),
                         params={'ref': GITHUB_BRANCH}, timeout=20)
    except Exception:
        return None
    if r.status_code == 200:
        return base64.b64decode(r.json()['content']).decode('utf-8')
    return None

def gh_put(path, text, message):
    """Create or update a file. Returns (ok, info)."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, 'no github credentials'
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
    try:
        r = requests.get(url, headers=gh_headers(),
                         params={'ref': GITHUB_BRANCH}, timeout=20)
        sha = r.json().get('sha') if r.status_code == 200 else None
    except Exception:
        sha = None
    body = {
        'message': message,
        'content': base64.b64encode(text.encode('utf-8')).decode('ascii'),
        'branch': GITHUB_BRANCH,
    }
    if sha:
        body['sha'] = sha
    try:
        r = requests.put(url, headers=gh_headers(), json=body, timeout=30)
    except Exception as e:
        return False, f'network: {e}'
    return (r.status_code in (200, 201)), r.text[:300]

# ---------------------------------------------------------------- registry editing

def _registry_block_re(tld):
    return re.compile(
        r'(<pre\b[^>]*\bdata-tld=["\']' + re.escape(tld) + r'["\'][^>]*>)'
        r'(.*?)'
        r'(</pre>)',
        re.DOTALL,
    )

def add_entry(tld, line):
    """Append `line` to the .tld block in domains/registry.html."""
    content = gh_get(REGISTRY)
    if content is None:
        return False, f'{REGISTRY} not found'

    m = _registry_block_re(tld).search(content)
    if not m:
        return False, f'no <pre data-tld="{tld}"> block in {REGISTRY}'

    existing = {ln.strip() for ln in m.group(2).splitlines() if ln.strip()}
    if line in existing:
        return True, 'already present'

    new_inner = (m.group(2).rstrip('\n') + '\n' + line + '\n').lstrip('\n')
    new_content = content[:m.start(2)] + new_inner + content[m.end(2):]
    return gh_put(REGISTRY, new_content, f'registry: add {line} → .{tld}')

# ---------------------------------------------------------------- routes

@app.route('/')
def home():
    return send_from_directory(ROOT, 'builder.html')

@app.route('/api/config')
def config():
    return jsonify(
        pages_url=pages_url(),
        free_tlds=sorted(FREE_TLDS),
        commit_enabled=bool(GITHUB_TOKEN and GITHUB_REPO),
    )

@app.route('/api/submit', methods=['POST'])
def submit():
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        return jsonify(ok=False, error='invalid json'), 400

    category = (data.get('category') or '').strip().lower()
    name     = (data.get('name') or '').strip()
    html     = data.get('html') or ''
    tld      = (data.get('tld') or '').strip().lower()

    if category not in CATEGORIES:
        return jsonify(ok=False, error='invalid category'), 400
    if not re.match(r'^[a-zA-Z0-9_-]{2,32}$', name):
        return jsonify(ok=False,
                       error='name must be 2–32 letters/numbers/dashes'), 400
    if len(html) < 50:
        return jsonify(ok=False, error='html too short (min 50 chars)'), 400
    if tld not in FREE_TLDS:
        return jsonify(ok=False, error='paid',
                       contact='https://mustjab-king-lyra.hf.space/'), 402

    if not (GITHUB_TOKEN and GITHUB_REPO):
        return jsonify(ok=False,
                       error='builder is running without GitHub credentials'), 500

    slug = name.lower()
    path = f'{category}/{slug}.html'

    if gh_get(path) is not None:
        return jsonify(ok=False,
                       error=f'{slug}.{tld} already taken'), 409

    # 1) publish the user's site
    ok, info = gh_put(path, html, f'Add {slug}.{tld} · Lyra Builder')
    if not ok:
        return jsonify(ok=False, error='site commit failed: ' + info), 500

    # 2) register the domain mapping
    ok2, info2 = add_entry(tld, f'{slug}={path}')
    if not ok2:
        return jsonify(ok=False, error='registry update failed: ' + info2), 500

    base = pages_url()
    return jsonify(
        ok=True,
        virtual=f'{slug}.{tld}',
        live=f'{base}/{path}',
        browser=f'{base}/index.html#{slug}.{tld}',
    )

@app.route('/<path:path>')
def static_any(path):
    return send_from_directory(ROOT, path)

# ---------------------------------------------------------------- main

if __name__ == '__main__':
    if not GITHUB_TOKEN:
        print('⚠️  GITHUB_TOKEN is not set — /api/submit will refuse to publish.')
    if not GITHUB_REPO:
        print('⚠️  GITHUB_REPOSITORY is not set — /api/submit will refuse to publish.')
    print(f'📄 registry: {REGISTRY}')
    print(f'🌐 pages url: {pages_url() or "(unknown)"}')
    print(f'🆓 free tlds: {sorted(FREE_TLDS)}')
    app.run(host='127.0.0.1', port=5000, threaded=True, debug=False)
