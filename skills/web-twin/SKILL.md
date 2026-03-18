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

> Based on [WebTwin](https://github.com/sirioberati/WebTwin) by **Sirio Berati** ([@heysirio](https://stan.store/heysirio)), licensed under MIT.
> Complete reference implementation is bundled in `reference/` directory of this skill.

## Module Structure

```
reference/
├── __init__.py      # Public API: extract_website, ExtractResult, Assets, Metadata, Components
├── models.py        # Data models (4 dataclasses)
├── extractor.py     # Main extraction orchestrator (11-step pipeline)
├── parser.py        # HTML/CSS parser (BeautifulSoup)
├── renderer.py      # Selenium headless Chrome renderer
├── downloader.py    # HTTP asset downloader (anti-detection)
├── utils.py         # URL and asset utility functions
├── logger.py        # Logging configuration
└── cli.py           # Command-line interface
```

## Dependencies

```
requests
beautifulsoup4
urllib3
# Optional (for JS rendering):
selenium
webdriver-manager
# Optional (for parser fallback):
html5lib
```

## Quick Start

The `reference/` directory is a self-contained Python package. You can use it directly:

```python
import sys
sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/skills/web-twin")
from reference import extract_website

# Basic extraction - saves everything to output_path
result = extract_website(
    "https://example.com",
    output_path="/tmp/my-clone",
)

# Access extraction results
print(result.metadata.title)           # Page title
print(len(result.assets.css))          # Number of CSS files
print(result.components.to_dict())     # Extracted UI components
print(result.output_path)              # Where files were saved
```

### Alternative: Copy into Your Project

If you prefer, you can also copy the `reference/` directory into your own project and rename it:

1. Copy `reference/` → `your_project/web_twin/`
2. Install dependencies: `pip install requests beautifulsoup4`
3. (Optional) Install Selenium: `pip install selenium webdriver-manager`
4. Import:

```python
from your_project.web_twin.extractor import extract_website

result = extract_website("https://example.com", output_path="./output")
```

## API Reference

### `extract_website(url, *, use_selenium=True, download_assets=True, output_path=None, timeout=30) -> ExtractResult`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | Target website URL (auto-adds `https://` if missing) |
| `use_selenium` | `bool` | `True` | Use headless Chrome for JS rendering |
| `download_assets` | `bool` | `True` | Download and save assets to disk |
| `output_path` | `str \| Path \| None` | `None` | Output directory (uses `/tmp/webtwin/` if None) |
| `timeout` | `int` | `30` | Request timeout in seconds |

### Return Type: `ExtractResult`

```python
@dataclass
class ExtractResult:
    url: str                    # Final URL (after redirects)
    html: str                   # Full HTML with absolute URLs
    assets: Assets              # All discovered asset URLs
    metadata: Metadata          # Page metadata (title, description, OG tags...)
    components: Components      # Extracted UI components
    output_path: Optional[Path] # Directory where files were saved

    def to_dict(self) -> dict    # JSON-serializable dictionary
```

### `Assets` Fields

| Field | Type | Description |
|-------|------|-------------|
| `css` | `list[str]` | CSS stylesheet URLs |
| `js` | `list[str]` | JavaScript file URLs |
| `img` | `list[str]` | Image URLs (including srcset, lazy-loaded) |
| `fonts` | `list[str]` | Font file URLs (.woff, .woff2, .ttf) |
| `videos` | `list[str]` | Video URLs |
| `audio` | `list[str]` | Audio URLs |
| `favicons` | `list[str]` | Favicon URLs |
| `font_families` | `set[str]` | Font family names used in CSS |

### `Components` Fields

Detected via HTML tags, CSS classes, and ARIA roles:

| Field | Detection Patterns |
|-------|-------------------|
| `navigation` | `<nav>`, `role="navigation"`, `.nav` classes |
| `header` | `<header>`, `role="banner"` |
| `footer` | `<footer>`, `role="contentinfo"` |
| `hero` | `.hero`, `.banner`, `.jumbotron` |
| `card` | `.card`, `.tile` |
| `form` | `<form>`, `.form` |
| `cta` | `.cta`, `.call-to-action` class names |
| `sidebar` | `.sidebar`, `.side-bar` class names |
| `modal` | `role="dialog"`, `.modal`, `.popup` |
| `section` | `<section>`, `.section` |
| `store` | `.product`, `.shop`, `.pricing` |
| `mobile` | `.mobile`, `.app-download` |
| `cart` | `.cart`, `.shopping-cart`, `.basket` |

Each component is `dict` with an `"html"` key containing the raw HTML snippet.

### `Metadata` Fields

`title`, `description`, `keywords`, `og_tags` (dict), `twitter_cards` (dict), `canonical`, `language`, `favicon`, `structured_data` (list of JSON-LD)

## Output Directory Structure

When `download_assets=True`, generates:

```
output_path/
├── index.html           # Main HTML (relative URLs → absolute)
├── metadata.json        # Page metadata as JSON
├── README.md            # Auto-generated documentation
├── css/                 # Downloaded stylesheets
│   └── fonts.css        # Google Fonts @import (if font_families found)
├── js/                  # Downloaded scripts
├── img/                 # Downloaded images
├── fonts/               # Downloaded font files
├── videos/              # Downloaded videos
├── audio/               # Downloaded audio
└── components/          # Extracted UI components
    ├── index.html       # Component preview page
    ├── navigation/      # Nav component HTML files
    ├── header/
    ├── card/
    └── ...
```

## Usage in Async Context (Celery / FastAPI)

`extract_website` is synchronous. In async code, wrap with `run_in_executor`:

```python
import asyncio
from web_twin.extractor import extract_website

async def crawl_page(url: str, output_dir: str):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: extract_website(url, output_path=output_dir),
    )
    return result
```

## How Extraction Works (11-Step Pipeline)

1. **URL normalization** - Add `https://` if missing
2. **HTML fetching** - Selenium (headless Chrome) first, HTTP fallback
3. **HTML parsing** - BeautifulSoup initialization
4. **Metadata extraction** - title, description, OG tags, JSON-LD
5. **Asset extraction** - CSS, JS, images, fonts from HTML tags
6. **Component extraction** - UI patterns by tag/class/role
7. **Merge Selenium URLs** - Add lazily-loaded resources found during scroll
8. **Regex fallback** - Pattern scan if <10 assets found
9. **URL fixing** - Convert relative URLs to absolute
10. **Result building** - Construct `ExtractResult`
11. **Save to directory** - Download all assets, generate output structure

## Extraction Strategies

### Multi-Level Degradation
```
Selenium (JS rendering, scrolling, clicking "Load More")
  ↓ fails
HTTP Downloader (static HTML only)
  ↓ both produce HTML
BeautifulSoup parsing (universal)
  ↓ few assets found
Regex pattern matching (edge cases)
```

### Anti-Detection Features
- User-Agent rotation (5 agents)
- Referer randomization (Google, Bing, Facebook, Twitter)
- 3 retries with fixed-delay backoff (1-3s)
- CSS animation disabling for faster rendering
- Headless Chrome with anti-automation flags

### Framework-Aware Extraction
- **Next.js**: `_next/static` chunks, `data-n-g` links
- **React**: webpack bundles, dynamic imports
- **Angular**: Angular-specific resource patterns

## Common Patterns

### Extract and analyze for cloning

```python
result = extract_website(url, output_path=str(page_dir))

# Use metadata for PRD generation
site_info = {
    "title": result.metadata.title,
    "description": result.metadata.description,
    "language": result.metadata.language,
}

# Use components for layout analysis
components = result.components.to_dict()
# e.g. {"navigation": [...], "header": [...], "card": [...]}

# Use assets for resource inventory
asset_summary = {
    "css_count": len(result.assets.css),
    "js_count": len(result.assets.js),
    "img_count": len(result.assets.img),
    "fonts": list(result.assets.font_families),
}
```

### Lightweight extraction (no file download)

```python
result = extract_website(
    url,
    download_assets=False,  # Don't save files
    use_selenium=False,     # Skip Selenium for speed
)
# result.html, result.metadata, result.components still available
# result.output_path will be None
```

### Check Selenium availability

```python
from web_twin.renderer import is_selenium_available

if is_selenium_available():
    result = extract_website(url)
else:
    result = extract_website(url, use_selenium=False)
```

## CLI Usage

WebTwin also provides a command-line interface:

```bash
python -m web_twin.cli <URL> [OPTIONS]

# Options:
#   -o, --output PATH      Output directory
#   --no-selenium          Disable JS rendering
#   --no-download          Don't download assets
#   --timeout SECONDS      Request timeout (default: 30)
#   -v, --version          Show version
```

## Debugging

Enable detailed logging with `setup_logging`:

```python
import logging
from web_twin import setup_logging

setup_logging(level=logging.DEBUG)  # See all extraction details
```

## Gotchas

1. **Synchronous API** - `extract_website` blocks. Always use `run_in_executor` in async contexts.
2. **Selenium dependency is optional** - If selenium/webdriver-manager not installed, automatically falls back to HTTP-only mode. Won't crash. But `html5lib` is also a soft dependency for parser fallback — if both `html.parser` and `html5lib` are missing, parsing may fail.
3. **Memory usage** - Large sites with many assets can use 100-500MB. Set `download_assets=False` if you only need HTML/metadata.
4. **CORS & auth** - Cannot extract content behind login walls or strict CORS. Only public pages.
5. **Rate limiting** - Rapid extraction of many pages from the same domain may trigger rate limiting. Use `asyncio.Semaphore(10)` for concurrent extraction (see `workflow_crawl.py` for reference).
6. **output_path None** - Creates temp directory at `/tmp/webtwin/{domain}_{timestamp}/`. Remember to clean up.
7. **Component detection** - Class-based detection works best on sites using common CSS frameworks (Bootstrap, Tailwind). Custom-styled sites may yield fewer components.
8. **Import path** - Adjust import path based on where you place the module in your project. The reference code uses relative imports internally (e.g., `from .extractor import extract_website`).
9. **SSL verification disabled** - Downloader sets `verify=False` for all requests. Be aware of security implications when extracting from untrusted URLs.
10. **Google Fonts assumption** - All detected `font_families` generate Google Fonts `@import` URLs. Custom or Adobe fonts will produce broken imports in `css/fonts.css`.
11. **Unknown asset type defaults to JS** - `get_asset_type()` returns `"js"` for unrecognized URLs. Non-JS files may end up in the `js/` directory.
