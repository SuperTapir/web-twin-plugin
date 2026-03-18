"""
webtwin - Website extraction library

Extract complete website content including HTML, CSS, JavaScript,
images, and UI components.

Example:
    >>> from webtwin import extract_website
    >>> result = extract_website("https://example.com")
    >>> print(result.metadata.title)
    >>> print(f"Found {len(result.assets.css)} CSS files")

    >>> # Save to output directory
    >>> result = extract_website("https://example.com", output_path="./site")
    >>> print(f"Saved to: {result.output_path}")

    >>> # Enable debug logging
    >>> import logging
    >>> from webtwin import setup_logging
    >>> setup_logging(level=logging.DEBUG)
"""

from .extractor import extract_website
from .logger import setup_logger as setup_logging
from .models import Assets, Components, ExtractResult, Metadata
from .renderer import is_selenium_available

__version__ = "0.1.0"
__all__ = [
    "extract_website",
    "ExtractResult",
    "Assets",
    "Metadata",
    "Components",
    "is_selenium_available",
    "setup_logging",
]
