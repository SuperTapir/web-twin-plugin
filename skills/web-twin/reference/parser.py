"""HTML/CSS parser for webtwin."""

import json
import re
from typing import Optional

from bs4 import BeautifulSoup

from .models import Assets, Components, Metadata
from .utils import get_asset_type, resolve_url


class Parser:
    """Parse HTML and extract assets, metadata, and components."""

    def __init__(self, html: str, base_url: str):
        self.html = html
        self.base_url = base_url
        self.soup = BeautifulSoup(html, "html.parser")

        # Fallback to html5lib if parsing fails
        if not self.soup or not self.soup.html:
            try:
                self.soup = BeautifulSoup(html, "html5lib")
            except Exception:
                # html5lib is optional; keep the html.parser result
                pass

    def extract_metadata(self) -> Metadata:
        """Extract metadata from HTML."""
        metadata = Metadata()

        # Title
        title_tag = self.soup.find("title")
        if title_tag and title_tag.string:
            metadata.title = title_tag.string.strip()

        # Meta tags
        for tag in self.soup.find_all("meta"):
            name = tag.get("name", "").lower()
            prop = tag.get("property", "").lower()
            content = tag.get("content", "").strip()

            if name == "description":
                metadata.description = content
            elif name == "keywords":
                metadata.keywords = content
            elif prop.startswith("og:"):
                metadata.og_tags[prop[3:]] = content
            elif name.startswith("twitter:"):
                metadata.twitter_cards[name[8:]] = content

        # Canonical URL
        canonical = self.soup.find("link", {"rel": "canonical"})
        if canonical and canonical.get("href"):
            metadata.canonical = resolve_url(canonical["href"], self.base_url)

        # Language
        html_tag = self.soup.find("html")
        if html_tag and html_tag.get("lang"):
            metadata.language = html_tag["lang"]

        # Favicon
        favicon = self.soup.find("link", {"rel": "icon"}) or self.soup.find(
            "link", {"rel": "shortcut icon"}
        )
        if favicon and favicon.get("href"):
            metadata.favicon = resolve_url(favicon["href"], self.base_url)

        # Structured data (JSON-LD)
        for script in self.soup.find_all("script", {"type": "application/ld+json"}):
            if script.string:
                try:
                    metadata.structured_data.append(json.loads(script.string))
                except json.JSONDecodeError:
                    pass

        return metadata

    def extract_assets(self) -> Assets:
        """Extract all assets from HTML."""
        assets = Assets()

        # CSS stylesheets
        for link in self.soup.find_all("link", {"rel": "stylesheet"}):
            href = link.get("href")
            if href:
                url = resolve_url(href, self.base_url)
                if url.startswith(("http://", "https://")):
                    assets.css.append(url)

        # Preload CSS
        for link in self.soup.find_all("link", {"rel": "preload", "as": "style"}):
            href = link.get("href")
            if href:
                url = resolve_url(href, self.base_url)
                if url.startswith(("http://", "https://")):
                    assets.css.append(url)

        # Next.js CSS
        for link in self.soup.find_all("link", {"data-n-g": True}):
            href = link.get("href")
            if href:
                url = resolve_url(href, self.base_url)
                if url.startswith(("http://", "https://")):
                    assets.css.append(url)

        # Inline styles - extract @import and fonts
        for style in self.soup.find_all("style"):
            if style.string:
                self._extract_from_css(style.string, assets)

        # JavaScript files
        for script in self.soup.find_all("script", {"src": True}):
            src = script.get("src")
            if src:
                url = resolve_url(src, self.base_url)
                if url.startswith(("http://", "https://")):
                    assets.js.append(url)

        # Module scripts
        for script in self.soup.find_all("script", {"type": "module"}):
            src = script.get("src")
            if src:
                url = resolve_url(src, self.base_url)
                if url.startswith(("http://", "https://")):
                    assets.js.append(url)

        # Images
        self._extract_images(assets)

        # Favicons
        for link in self.soup.find_all("link", {"rel": lambda r: r and "icon" in r.lower()}):
            href = link.get("href")
            if href:
                url = resolve_url(href, self.base_url)
                if url.startswith(("http://", "https://")):
                    assets.favicons.append(url)

        # Videos
        for video in self.soup.find_all("video"):
            src = video.get("src")
            if src:
                url = resolve_url(src, self.base_url)
                if url.startswith(("http://", "https://")):
                    assets.videos.append(url)
            for source in video.find_all("source"):
                src = source.get("src")
                if src:
                    url = resolve_url(src, self.base_url)
                    if url.startswith(("http://", "https://")):
                        assets.videos.append(url)

        # Audio
        for audio in self.soup.find_all("audio"):
            src = audio.get("src")
            if src:
                url = resolve_url(src, self.base_url)
                if url.startswith(("http://", "https://")):
                    assets.audio.append(url)
            for source in audio.find_all("source"):
                src = source.get("src")
                if src:
                    url = resolve_url(src, self.base_url)
                    if url.startswith(("http://", "https://")):
                        assets.audio.append(url)

        # Iframes (YouTube, Vimeo)
        for iframe in self.soup.find_all("iframe"):
            src = iframe.get("src")
            if src and not src.startswith("data:"):
                url = resolve_url(src, self.base_url)
                if "youtube" in url or "vimeo" in url:
                    assets.videos.append(url)

        # Extract Next.js specific resources
        self._extract_nextjs_assets(assets)

        # Remove duplicates
        assets.css = list(dict.fromkeys(assets.css))
        assets.js = list(dict.fromkeys(assets.js))
        assets.img = list(dict.fromkeys(assets.img))
        assets.fonts = list(dict.fromkeys(assets.fonts))
        assets.videos = list(dict.fromkeys(assets.videos))
        assets.audio = list(dict.fromkeys(assets.audio))
        assets.favicons = list(dict.fromkeys(assets.favicons))

        return assets

    def _extract_images(self, assets: Assets):
        """Extract images from HTML."""
        for img in self.soup.find_all("img"):
            # src attribute
            src = img.get("src")
            if src and not src.startswith("data:"):
                url = resolve_url(src, self.base_url)
                if url.startswith(("http://", "https://")):
                    assets.img.append(url)

            # srcset attribute
            srcset = img.get("srcset")
            if srcset:
                for src_str in srcset.split(","):
                    parts = src_str.strip().split(" ")
                    if parts:
                        url = resolve_url(parts[0], self.base_url)
                        if url.startswith(("http://", "https://")):
                            assets.img.append(url)

            # data-src (lazy loading)
            data_src = img.get("data-src")
            if data_src and not data_src.startswith("data:"):
                url = resolve_url(data_src, self.base_url)
                if url.startswith(("http://", "https://")):
                    assets.img.append(url)

        # Background images in style attributes
        for elem in self.soup.select("[style]"):
            style = elem.get("style", "")
            if "background" in style:
                for match in re.findall(r"url\(['\"]?([^'\"|\)]+)['\"]?\)", style):
                    if not match.startswith("data:"):
                        url = resolve_url(match, self.base_url)
                        if url.startswith(("http://", "https://")):
                            assets.img.append(url)

    def _extract_from_css(self, css_content: str, assets: Assets):
        """Extract URLs and fonts from CSS content."""
        # @import statements
        for match in re.findall(r'@import\s+[\'"]([^\'"]+)[\'"]', css_content):
            url = resolve_url(match, self.base_url)
            if url.startswith(("http://", "https://")):
                assets.css.append(url)

        for match in re.findall(r"@import\s+url\(['\"]?([^'\"|\)]+)['\"]?\)", css_content):
            url = resolve_url(match, self.base_url)
            if url.startswith(("http://", "https://")):
                assets.css.append(url)

        # Font families
        for match in re.findall(r"font-family:\s*['\"]?([^'\";]+)['\"]?", css_content):
            family = match.strip().split(",")[0].strip("'\"` ")
            if family.lower() not in (
                "serif",
                "sans-serif",
                "monospace",
                "cursive",
                "fantasy",
                "system-ui",
            ):
                assets.font_families.add(family)

    def _extract_nextjs_assets(self, assets: Assets):
        """Extract Next.js specific resources."""
        next_data = self.soup.find("script", {"id": "__NEXT_DATA__"})
        if next_data and next_data.string:
            try:
                data = json.loads(next_data.string)
                if "buildId" in data:
                    build_id = data["buildId"]
                    # Add common Next.js chunks
                    for path in ["main", "webpack", "framework"]:
                        chunk_url = f"{self.base_url}/_next/static/{build_id}/pages/{path}.js"
                        assets.js.append(chunk_url)
            except json.JSONDecodeError:
                pass

    def extract_components(self) -> Components:
        """Extract UI components from HTML."""
        components = Components()

        # Navigation
        nav_elements = (
            self.soup.find_all("nav")
            + self.soup.find_all(role="navigation")
            + self.soup.find_all(class_=lambda c: c and ("nav" in str(c).lower() or "menu" in str(c).lower()))
        )
        for elem in nav_elements[:5]:
            components.navigation.append({"html": str(elem)})

        # Header
        header_elements = (
            self.soup.find_all("header")
            + self.soup.find_all(role="banner")
            + self.soup.find_all(class_=lambda c: c and "header" in str(c).lower())
        )
        for elem in header_elements[:2]:
            components.header.append({"html": str(elem)})

        # Footer
        footer_elements = (
            self.soup.find_all("footer")
            + self.soup.find_all(role="contentinfo")
            + self.soup.find_all(class_=lambda c: c and "footer" in str(c).lower())
        )
        for elem in footer_elements[:2]:
            components.footer.append({"html": str(elem)})

        # Hero sections
        hero_elements = self.soup.find_all(
            class_=lambda c: c
            and ("hero" in str(c).lower() or "banner" in str(c).lower() or "jumbotron" in str(c).lower())
        )
        for elem in hero_elements[:3]:
            components.hero.append({"html": str(elem)})

        # Cards
        card_elements = self.soup.find_all(
            class_=lambda c: c and ("card" in str(c).lower() or "tile" in str(c).lower())
        )
        unique_cards = {}
        for elem in card_elements[:15]:
            structure_hash = str(len(elem.find_all()))
            if structure_hash not in unique_cards:
                unique_cards[structure_hash] = elem
        for elem in list(unique_cards.values())[:5]:
            components.card.append({"html": str(elem)})

        # Forms
        form_elements = self.soup.find_all("form") + self.soup.find_all(
            class_=lambda c: c and "form" in str(c).lower()
        )
        for elem in form_elements[:3]:
            components.form.append({"html": str(elem)})

        # CTAs
        cta_elements = self.soup.find_all(
            class_=lambda c: c and ("cta" in str(c).lower() or "call-to-action" in str(c).lower())
        )
        for elem in cta_elements[:3]:
            components.cta.append({"html": str(elem)})

        # Sidebars
        sidebar_elements = self.soup.find_all(
            class_=lambda c: c and ("sidebar" in str(c).lower() or "side-bar" in str(c).lower())
        )
        for elem in sidebar_elements[:2]:
            components.sidebar.append({"html": str(elem)})

        # Modals
        modal_elements = self.soup.find_all(role="dialog") + self.soup.find_all(
            class_=lambda c: c
            and ("modal" in str(c).lower() or "dialog" in str(c).lower() or "popup" in str(c).lower())
        )
        for elem in modal_elements[:3]:
            components.modal.append({"html": str(elem)})

        # Sections
        section_elements = self.soup.find_all("section") + self.soup.find_all(role="region")
        substantial = [e for e in section_elements if len(e.find_all()) > 3]
        for elem in substantial[:5]:
            components.section.append({"html": str(elem)})

        # Store/product components
        store_elements = self.soup.find_all(
            class_=lambda c: c
            and (
                "product" in str(c).lower()
                or "store" in str(c).lower()
                or "shop" in str(c).lower()
                or "pricing" in str(c).lower()
            )
        )
        for elem in store_elements[:5]:
            components.store.append({"html": str(elem)})

        # Mobile components
        mobile_elements = self.soup.find_all(
            class_=lambda c: c
            and ("mobile" in str(c).lower() or "smartphone" in str(c).lower() or "mobile-only" in str(c).lower())
        )
        for elem in mobile_elements[:3]:
            components.mobile.append({"html": str(elem)})

        # Cart components
        cart_elements = self.soup.find_all(
            class_=lambda c: c
            and ("cart" in str(c).lower() or "basket" in str(c).lower() or "shopping-cart" in str(c).lower())
        )
        for elem in cart_elements[:2]:
            components.cart.append({"html": str(elem)})

        return components

    def fix_relative_urls(self) -> str:
        """Fix relative URLs in HTML and return modified HTML."""
        # Fix links
        for link in self.soup.find_all("a", href=True):
            if link["href"].startswith("/"):
                link["href"] = resolve_url(link["href"], self.base_url)

        # Fix images
        for img in self.soup.find_all("img", src=True):
            if not img["src"].startswith(("http://", "https://", "data:")):
                img["src"] = resolve_url(img["src"], self.base_url)

        # Fix scripts
        for script in self.soup.find_all("script", src=True):
            if not script["src"].startswith(("http://", "https://", "data:")):
                script["src"] = resolve_url(script["src"], self.base_url)

        # Fix stylesheets
        for link in self.soup.find_all("link", href=True):
            if not link["href"].startswith(("http://", "https://", "data:")):
                link["href"] = resolve_url(link["href"], self.base_url)

        return str(self.soup)

    def extract_additional_assets_from_patterns(self, assets: Assets):
        """Extract additional assets using regex patterns on raw HTML."""
        patterns = [
            r"[\"'](https?://[^\"']+\.(css|js|png|jpg|jpeg|gif|svg|woff2?))[\"']",
            r"[\"'](/[^\"']+\.(css|js|png|jpg|jpeg|gif|svg|woff2?))[\"']",
            r"[\"'](//[^\"']+\.(css|js|png|jpg|jpeg|gif|svg|woff2?))[\"']",
        ]

        for pattern in patterns:
            for match in re.findall(pattern, self.html):
                url = match[0] if isinstance(match, tuple) else match
                url = resolve_url(url, self.base_url)

                if "{" in url or "}" in url:
                    continue

                asset_type = get_asset_type(url)
                if asset_type == "css" and url not in assets.css:
                    assets.css.append(url)
                elif asset_type == "js" and url not in assets.js:
                    assets.js.append(url)
                elif asset_type == "img" and url not in assets.img:
                    assets.img.append(url)
                elif asset_type == "fonts" and url not in assets.fonts:
                    assets.fonts.append(url)
