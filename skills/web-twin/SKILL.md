---
description: >
  Website extraction, cloning, and resource crawling using the web_twin module.
  Use when you need to clone a website, extract website content, download HTML/CSS/JS/image assets,
  parse UI components from a page, render JavaScript-heavy sites, or build url2app workflows.
  Trigger on: "web_twin", "extract website", "clone site", "crawl page", "website assets",
  "UI components extraction", "selenium render", "url2app", "website cloning",
  "download website resources", "extract page layout", "scrape website structure",
  "scrape", "download page", "website to app", "site to app", "page resources",
  "workflow_crawl", "webtwin cli".
---

# WebTwin - Website Extraction & Cloning

> Based on [WebTwin](https://github.com/sirioberati/WebTwin) by **Sirio Berati**, MIT license.

## How to Use (Follow This Order)

### Step 1: Ensure dependencies are installed

Run this FIRST, every time. Do NOT skip.

```bash
pip install requests beautifulsoup4 urllib3 2>/dev/null
```

Selenium is optional (for JS-rendered pages). Check with:

```bash
python3 -c "import selenium; print('ok')" 2>/dev/null && echo "Selenium available" || echo "Selenium not available, will use HTTP fallback"
```

### Step 2: Run extraction

Write a single Python script. The `reference/` directory inside this skill is a ready-to-use package.

```python
import sys
sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/skills/web-twin")
from reference import extract_website, is_selenium_available

url = "TARGET_URL_HERE"
output_dir = "/tmp/webtwin-output"

result = extract_website(
    url,
    output_path=output_dir,
    use_selenium=is_selenium_available(),  # auto-detect
)

print(f"Title: {result.metadata.title}")
print(f"CSS: {len(result.assets.css)}, JS: {len(result.assets.js)}, Images: {len(result.assets.img)}")
print(f"Components: {list(k for k, v in result.components.to_dict().items() if v)}")
print(f"Saved to: {result.output_path}")
```

That's it. The module handles Selenium fallback, anti-detection, and asset downloading automatically.

### Step 3: Present results

Summarize: title, resource counts, detected components, output path.

## API Reference

### `extract_website(url, *, use_selenium=True, download_assets=True, output_path=None, timeout=30) -> ExtractResult`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | Target URL (auto-adds `https://`) |
| `use_selenium` | `bool` | `True` | Headless Chrome for JS rendering |
| `download_assets` | `bool` | `True` | Download assets to disk |
| `output_path` | `str \| Path \| None` | `None` | Output dir (default: `/tmp/webtwin/`) |
| `timeout` | `int` | `30` | Request timeout in seconds |

### `is_selenium_available() -> bool`

Returns whether Selenium + webdriver-manager are importable. Use this to set `use_selenium` parameter.

### Return: `ExtractResult`

```python
result.url           # str - final URL after redirects
result.html          # str - full HTML
result.metadata      # Metadata - title, description, og_tags, language, etc.
result.assets        # Assets - css, js, img, fonts, videos, audio, favicons lists
result.components    # Components - navigation, header, footer, hero, card, form, etc.
result.output_path   # Path - where files were saved
result.to_dict()     # dict - JSON-serializable
```

### Components (13 types)

`navigation`, `header`, `footer`, `hero`, `card`, `form`, `cta`, `sidebar`, `modal`, `section`, `store`, `mobile`, `cart`

Each is a list of dicts with `"html"` key.

## Output Directory

```
output_path/
├── index.html       # Page HTML
├── metadata.json    # Metadata as JSON
├── css/             # Stylesheets
├── js/              # Scripts
├── img/             # Images
├── fonts/           # Font files
└── components/      # UI component HTML snippets
```

## Lightweight Mode (No Download)

```python
result = extract_website(url, download_assets=False, use_selenium=False)
# Only result.html, result.metadata, result.components — no files saved
```

## Gotchas

1. **Always use `is_selenium_available()`** to set `use_selenium`. Do NOT assume Selenium is installed.
2. **Synchronous API** — blocks the thread. In async contexts, wrap with `asyncio.loop.run_in_executor()`.
3. **Public pages only** — cannot extract content behind login walls or CORS restrictions.
4. **Memory** — large sites may use 100-500MB. Use `download_assets=False` for metadata-only extraction.
5. **SSL verification disabled** — downloader uses `verify=False`. Be aware of security implications.
6. **Google Fonts assumption** — detected `font_families` generate Google Fonts imports. Custom fonts produce broken URLs.
7. **Temp dir cleanup** — when `output_path=None`, files go to `/tmp/webtwin/`. Remember to clean up.
