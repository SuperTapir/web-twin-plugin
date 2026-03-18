# web-twin

[简体中文](./README.zh-CN.md)

Claude Code plugin for website extraction, cloning, and resource crawling.

> Based on [WebTwin](https://github.com/sirioberati/WebTwin) by [Sirio Berati](https://stan.store/heysirio) ([@heysirio](https://github.com/sirioberati)), MIT license.

## What It Does

Once installed, Claude automatically gains full knowledge of the `web_twin` module whenever you ask it to clone or extract a website:

- Call `extract_website()` to grab HTML, CSS, JS, images, and fonts
- Extract UI components (navigation, cards, forms — 13 types in total)
- Handle JavaScript-rendered pages via headless Selenium
- Best practices for async calls, anti-detection, and multi-level fallback

**Zero manual setup** — just install the plugin and tell Claude "clone this website".

## Install

### Option A: Marketplace (Recommended)

```bash
claude plugin marketplace add SuperTapir/web-twin-plugin
claude plugin install web-twin@web-twin-plugin
```

### Option B: Git Clone

```bash
git clone https://github.com/SuperTapir/web-twin-plugin.git ~/.claude/skills/web-twin-plugin
```

Then add to your project's `.claude/settings.json`:

```json
{
  "skills": ["~/.claude/skills/web-twin-plugin/skills/web-twin"]
}
```

Or copy the skill folder directly into your project:

```bash
cp -r web-twin-plugin/skills/web-twin .claude/skills/web-twin
```

### Start Using

```
> Extract the website resources and UI components from https://example.com

> Use web_twin to scrape this page and analyze its layout

> Clone this website's design, extract all CSS and images
```

## Trigger Phrases

The skill activates automatically when your conversation mentions:

| Scenario | Trigger Words |
|----------|---------------|
| Website cloning | "clone site", "extract website", "website cloning" |
| Resource crawling | "scrape", "crawl page", "download page" |
| Component extraction | "UI components", "extract components" |
| Module invocation | "web_twin", "webtwin", "extract_website" |
| Workflow | "url2app", "website to app" |

## Core Capabilities

```
Selenium headless browser rendering (JS dynamic content)
  ↓ falls back on failure
HTTP static download
  ↓ produces HTML
BeautifulSoup parsing
  ↓ too few assets
Regex supplementary scan
```

- **11-step extraction pipeline**: URL normalization → rendering → parsing → metadata/assets/components extraction → output
- **Anti-detection**: User-Agent rotation, Referer randomization, retry mechanism
- **Framework-aware**: Next.js / React / Angular specific resource extraction
- **13 UI component types**: navigation, header, footer, hero, card, form, CTA, sidebar, modal, section, store, mobile, cart

## Plugin Structure

```
web-twin-plugin/
├── .claude-plugin/plugin.json       # Plugin manifest
├── LICENSE                          # MIT license
├── README.md
├── README.zh-CN.md                  # 中文文档
└── skills/web-twin/
    ├── SKILL.md                     # Skill documentation (auto-loaded by Claude)
    └── reference/                   # Full module source code
        ├── __init__.py              # Public API
        ├── extractor.py             # Main extractor (11-step pipeline)
        ├── parser.py                # HTML/CSS parser
        ├── renderer.py              # Selenium renderer
        ├── downloader.py            # HTTP downloader (anti-detection)
        ├── models.py                # Data models
        ├── utils.py                 # Utility functions
        ├── logger.py                # Logging
        ├── cli.py                   # CLI interface
        └── requirements.txt         # Python dependencies
```

## Credits

Based on [WebTwin](https://github.com/sirioberati/WebTwin) by **Sirio Berati**.

- Original repo: https://github.com/sirioberati/WebTwin
- Author: https://stan.store/heysirio

## License

MIT — see [LICENSE](./LICENSE).
