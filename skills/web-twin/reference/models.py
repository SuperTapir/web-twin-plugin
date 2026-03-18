"""Data models for webtwin."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Metadata:
    """Website metadata."""

    title: str = ""
    description: str = ""
    keywords: str = ""
    og_tags: dict = field(default_factory=dict)
    twitter_cards: dict = field(default_factory=dict)
    canonical: str = ""
    language: str = ""
    favicon: str = ""
    structured_data: list = field(default_factory=list)


@dataclass
class Assets:
    """Extracted website assets."""

    css: list[str] = field(default_factory=list)
    js: list[str] = field(default_factory=list)
    img: list[str] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)
    videos: list[str] = field(default_factory=list)
    audio: list[str] = field(default_factory=list)
    favicons: list[str] = field(default_factory=list)
    font_families: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "css": self.css,
            "js": self.js,
            "img": self.img,
            "fonts": self.fonts,
            "videos": self.videos,
            "audio": self.audio,
            "favicons": self.favicons,
            "font_families": list(self.font_families),
        }


@dataclass
class Components:
    """Extracted UI components."""

    navigation: list[dict] = field(default_factory=list)
    header: list[dict] = field(default_factory=list)
    footer: list[dict] = field(default_factory=list)
    hero: list[dict] = field(default_factory=list)
    card: list[dict] = field(default_factory=list)
    form: list[dict] = field(default_factory=list)
    cta: list[dict] = field(default_factory=list)
    sidebar: list[dict] = field(default_factory=list)
    modal: list[dict] = field(default_factory=list)
    section: list[dict] = field(default_factory=list)
    store: list[dict] = field(default_factory=list)
    mobile: list[dict] = field(default_factory=list)
    cart: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding empty lists."""
        result = {}
        for key in [
            "navigation",
            "header",
            "footer",
            "hero",
            "card",
            "form",
            "cta",
            "sidebar",
            "modal",
            "section",
            "store",
            "mobile",
            "cart",
        ]:
            value = getattr(self, key)
            if value:
                result[key] = value
        return result


@dataclass
class ExtractResult:
    """Result of website extraction."""

    url: str
    html: str
    assets: Assets
    metadata: Metadata
    components: Components
    output_path: Optional[Path] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "html": self.html,
            "assets": self.assets.to_dict(),
            "metadata": self.metadata.__dict__,
            "components": self.components.to_dict(),
            "output_path": str(self.output_path) if self.output_path else None,
        }
