# Lyra Builder — by Muhammad Taqi

A web‑publisher system.

- **Builder** (`builder.html`) runs on a temporary **TryCloudflare** tunnel,
  refreshed every 2 hours by GitHub Actions. URL is always written to `url.txt`.
- **Browser** (`index.html`) runs on **GitHub Pages**, lists every published
  site, and resolves virtual domains like `#taqi.mt → ai/taqi.html`.
- **Registry** (`domains/registry.html`) is the single source of truth for all
  TLDs — each TLD lives in its own `<pre class="lyra-target" data-tld="…">`
  block with `name=category/file.html` lines.

---

## Folder layout

├── .github/workflows/
│ ├── builder-tunnel.yml # trycloudflare + url.txt refresh every 2h
│ └── pages.yml # deploys the whole repo to GitHub Pages
├── ai/
│ └── taqi.html # sample site (mapped to taqi.mt)
├── web/.gitkeep
├── game/.gitkeep
├── other/.gitkeep
├── domains/
│ └── registry.html # ← single file, all TLDs
├── scripts/
│ ├── server.py # Flask backend (builder + /api/submit)
│ └── init_domains.py # regenerates domains/registry.html
├── builder.html # 3‑step builder UI (served via tunnel)
├── index.html # Lyra Browser (served via GitHub Pages)
├── dummy.txt # heartbeat, rewritten every 2h
├── url.txt # current tunnel URL, rewritten every 2h
└── README.md

