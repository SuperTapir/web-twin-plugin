# web-twin

Claude Code plugin for website extraction, cloning, and resource crawling.

> Based on [WebTwin](https://github.com/sirioberati/WebTwin) by [Sirio Berati](https://stan.store/heysirio) ([@heysirio](https://github.com/sirioberati)), licensed under MIT.

## What it does

When you ask Claude to clone or extract a website, this skill provides:

- **Complete API reference** for the `web_twin` module
- **Ready-to-use source code** in `reference/` directory (copy into your project)
- **Usage patterns** for extracting HTML, CSS, JS, images, fonts, and UI components
- **Integration guidance** for async contexts (FastAPI, Celery)
- **Gotchas and best practices** to avoid common pitfalls

## Trigger phrases

The skill activates when you mention:

- "extract website", "clone site", "scrape", "crawl page"
- "download page", "website assets", "UI components extraction"
- "website to app", "url2app", "selenium render"
- "web_twin", "webtwin"

## Features

- **11-step extraction pipeline**: URL normalization → Selenium/HTTP fetch → HTML parsing → metadata/assets/components extraction → output generation
- **Multi-level degradation**: Selenium → HTTP → Regex fallback
- **Anti-detection**: User-Agent rotation, Referer randomization
- **Framework-aware**: Next.js, React, Angular specific resource extraction
- **13 UI component types**: navigation, header, footer, hero, card, form, CTA, sidebar, modal, section, store, mobile, cart

## Installation

```bash
claude plugin install /path/to/web-twin-plugin
```

Or add to your project's `.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "/path/to/web-twin-plugin": true
  }
}
```

## Integration

1. Copy `skills/web-twin/reference/` into your project as `web_twin/`
2. Install dependencies: `pip install requests beautifulsoup4`
3. (Optional) For JS rendering: `pip install selenium webdriver-manager`

```python
from web_twin.extractor import extract_website

result = extract_website("https://example.com", output_path="./output")
print(result.metadata.title)
print(result.components.to_dict())
```

## Credits

This plugin is based on [WebTwin](https://github.com/sirioberati/WebTwin) by **Sirio Berati**. The original project provides the core website extraction engine.

- Original repo: https://github.com/sirioberati/WebTwin
- Author: https://stan.store/heysirio

## License

MIT — see the [original LICENSE](https://github.com/sirioberati/WebTwin/blob/main/LICENSE) for full terms.
