# Lyra Builder — by Muhammad Taqi

A web-publisher system: users open the **TryCloudflare** builder, choose a
category (AI · Web · Game · Others), paste HTML, pick a domain, and the site is
committed straight into the GitHub repo. The **Lyra Browser** on GitHub Pages
then lists every site and resolves virtual domains like `#taqi.mt → ai/taqi.html`.

## Setup

1. Push this repo to GitHub.
2. Settings → Pages → Source = **GitHub Actions**.
3. Settings → Actions → General → Workflow permissions = **Read and write**.
4. (Optional) Repo → Settings → Variables → add `PAGES_URL`
   (e.g. `https://USERNAME.github.io/REPO`) if you don't want it auto-derived.
5. Run **Lyra Builder · TryCloudflare tunnel** from the Actions tab — the URL
   appears in the job summary. Open it and start publishing.

## How domain resolution works

Each file in `domains/` (e.g. `domains/mt.html`) contains:

```html
<pre class="lyra-target">
taqi=ai/taqi.html
</pre>
