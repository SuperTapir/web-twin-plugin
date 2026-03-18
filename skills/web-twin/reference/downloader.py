"""Asset downloader for webtwin."""

import random
import time
from typing import Optional

import requests
import urllib3

from .logger import logger
from .utils import is_valid_url

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://www.facebook.com/",
    "https://www.twitter.com/",
]


class Downloader:
    """HTTP downloader with retry and anti-detection."""

    def __init__(
        self,
        timeout: int = 15,
        max_retries: int = 3,
        delay: float = 0.1,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay
        self.session = requests.Session()

    def _get_headers(self, base_url: str) -> dict:
        """Generate request headers."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": base_url,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

    def _get_page_headers(self) -> dict:
        """Generate headers for fetching HTML pages."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Referer": random.choice(REFERERS),
        }

    def fetch_page(self, url: str) -> tuple[Optional[str], str]:
        """
        Fetch HTML page content.

        Returns:
            Tuple of (html_content, final_url)
        """
        logger.info(f"Fetching page: {url}")
        headers = self._get_page_headers()
        retry_count = 0

        while retry_count < self.max_retries:
            try:
                logger.debug(f"  Attempt {retry_count + 1}/{self.max_retries}")
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    headers=headers,
                    allow_redirects=True,
                    verify=False,
                )

                # Update URL if redirected
                final_url = response.url if response.history else url
                if response.history:
                    logger.info(f"  Redirected to: {final_url}")

                if response.status_code == 200:
                    # Determine encoding
                    encoding = self._detect_encoding(response)
                    try:
                        html = response.content.decode(encoding, errors="replace")
                    except (UnicodeDecodeError, LookupError):
                        html = response.content.decode("utf-8", errors="replace")
                    logger.info(f"  Fetched {len(html):,} bytes")
                    return html, final_url

                elif response.status_code in (403, 429, 503):
                    logger.warning(f"  HTTP {response.status_code}, retrying...")
                    # Rotate headers and retry
                    headers["User-Agent"] = random.choice(USER_AGENTS)
                    headers["Referer"] = random.choice(REFERERS)
                    time.sleep(random.uniform(1.0, 3.0))
                    retry_count += 1
                    continue

                else:
                    logger.error(f"  HTTP {response.status_code}")
                    return None, url

            except requests.exceptions.Timeout:
                logger.warning(f"  Timeout, retrying...")
                retry_count += 1
                time.sleep(1)
            except requests.exceptions.ConnectionError:
                logger.warning(f"  Connection error, retrying...")
                retry_count += 1
                time.sleep(2)
            except requests.exceptions.TooManyRedirects:
                logger.error(f"  Too many redirects")
                return None, url
            except Exception as e:
                logger.error(f"  Error: {e}")
                return None, url

        logger.error(f"  Failed after {self.max_retries} attempts")
        return None, url

    def _detect_encoding(self, response: requests.Response) -> str:
        """Detect encoding from response."""
        content_type = response.headers.get("Content-Type", "")

        # From Content-Type header
        if "charset=" in content_type:
            encoding = content_type.split("charset=")[1].split(";")[0].strip()
            return encoding

        # From response
        if response.encoding and response.encoding.lower() != "iso-8859-1":
            return response.encoding

        if response.apparent_encoding:
            return response.apparent_encoding

        return "utf-8"

    def download_asset(self, url: str, base_url: str) -> Optional[bytes]:
        """
        Download an asset from URL.

        Returns:
            Asset content as bytes, or None if failed.
        """
        content, _ = self.download_asset_with_reason(url, base_url)
        return content

    def download_asset_with_reason(self, url: str, base_url: str) -> tuple[Optional[bytes], Optional[str]]:
        """
        Download an asset from URL with failure reason.

        Returns:
            Tuple of (content, error_reason). If successful, error_reason is None.
        """
        if not is_valid_url(url):
            return None, "Invalid URL"

        headers = self._get_headers(base_url)
        retry_count = 0
        last_error = None

        # Small delay to avoid rate limiting
        time.sleep(self.delay)

        while retry_count < self.max_retries:
            try:
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    headers=headers,
                    stream=True,
                    allow_redirects=True,
                    verify=False,
                )

                if response.status_code == 200:
                    content = response.content
                    logger.debug(f"  Downloaded: {url[:60]}... ({len(content):,} bytes)")
                    return content, None

                elif response.status_code == 403:
                    last_error = "403 Forbidden"
                    headers["User-Agent"] = random.choice(USER_AGENTS)
                    retry_count += 1
                    time.sleep(1)

                elif response.status_code == 404:
                    return None, "404 Not Found"

                elif response.status_code >= 500:
                    last_error = f"{response.status_code} Server Error"
                    retry_count += 1
                    time.sleep(1)

                else:
                    return None, f"HTTP {response.status_code}"

            except requests.exceptions.Timeout:
                last_error = "Timeout"
                retry_count += 1
                time.sleep(1)
            except requests.exceptions.ConnectionError:
                last_error = "Connection Error"
                retry_count += 1
                time.sleep(1)
            except Exception as e:
                return None, str(e)

        return None, f"{last_error} (after {self.max_retries} retries)"

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
