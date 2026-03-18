"""Utility functions for webtwin."""

import re
from urllib.parse import urljoin, urlparse


def normalize_url(url: str) -> str:
    """Normalize URL by adding https:// if missing."""
    if not url:
        return url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def resolve_url(url: str, base_url: str) -> str:
    """Resolve relative URL against base URL."""
    if not url:
        return ""
    if url.startswith("data:"):
        return url
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith(("http://", "https://")):
        return urljoin(base_url, url)
    return url


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


def safe_filename(name: str, max_length: int = 100) -> str:
    """Convert string to safe filename."""
    # Remove or replace invalid characters
    safe = re.sub(r'[^\w\-_.]', '_', name)
    # Limit length
    if len(safe) > max_length:
        safe = safe[:max_length]
    return safe


def get_asset_type(url: str) -> str:
    """Determine the type of asset from the URL."""
    if not url:
        return "other"

    url_lower = url.lower()

    # Framework-specific patterns
    if "_next/static" in url_lower:
        if ".css" in url_lower or "styles" in url_lower:
            return "css"
        return "js"

    if "chunk." in url_lower or "webpack" in url_lower:
        return "js"

    if "angular" in url_lower and ".js" in url_lower:
        return "js"

    # CSS files
    if url_lower.endswith((".css", ".scss", ".less", ".sass")):
        return "css"
    if "global.css" in url_lower or "globals.css" in url_lower or "tailwind" in url_lower:
        return "css"
    if "fonts.googleapis.com" in url_lower:
        return "css"
    if "styles" in url_lower and ".css" in url_lower:
        return "css"

    # JS files
    if url_lower.endswith((".js", ".jsx", ".mjs", ".ts", ".tsx", ".cjs")):
        return "js"
    if "bundle.js" in url_lower or "main.js" in url_lower or "app.js" in url_lower:
        return "js"
    if "polyfill" in url_lower or "runtime" in url_lower or "vendor" in url_lower:
        return "js"

    # Image files
    if url_lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif", ".bmp", ".ico")):
        return "img"
    if "/images/" in url_lower or "/img/" in url_lower:
        return "img"

    # Font files
    if url_lower.endswith((".woff", ".woff2", ".ttf", ".otf", ".eot")):
        return "fonts"
    if "/fonts/" in url_lower or "font-awesome" in url_lower:
        return "fonts"

    # Media files
    if url_lower.endswith((".mp4", ".webm", ".ogg", ".avi", ".mov", ".flv")):
        return "videos"
    if url_lower.endswith((".mp3", ".wav", ".aac")):
        return "audio"

    # Favicon
    if url_lower.endswith((".ico", ".icon")) or "favicon" in url_lower:
        return "favicons"

    # Try to guess based on URL structure
    if "/css/" in url_lower:
        return "css"
    if "/js/" in url_lower or "/scripts/" in url_lower:
        return "js"

    return "js"  # Default


def is_binary_content(content: bytes, asset_type: str) -> bool:
    """Determine if content should be treated as binary."""
    if asset_type in ("img", "fonts", "videos", "audio", "favicons"):
        return True

    if asset_type in ("css", "js", "html"):
        if not isinstance(content, bytes):
            return False
        try:
            if b"\x00" in content:
                return True
            sample = content[:1024]
            text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
            return bool(sample.translate(None, text_chars))
        except Exception:
            return True

    return isinstance(content, bytes)
