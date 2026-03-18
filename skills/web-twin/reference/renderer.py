"""Selenium renderer for webtwin."""

import time
from typing import Optional

# Try to import Selenium
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from webdriver_manager.chrome import ChromeDriverManager

    SELENIUM_AVAILABLE = True
except ImportError:
    pass

# Import logger after selenium check
if SELENIUM_AVAILABLE:
    from .logger import logger


class SeleniumRenderer:
    """Render pages using Selenium with Chrome."""

    def __init__(self, timeout: int = 30):
        if not SELENIUM_AVAILABLE:
            raise ImportError(
                "Selenium is not installed. Run: pip install selenium webdriver-manager"
            )
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None

    def _create_driver(self) -> webdriver.Chrome:
        """Create Chrome WebDriver with anti-detection options."""
        logger.info("Starting Chrome WebDriver...")
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")

        # Anti-detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Modern user agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )

        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            logger.info("  WebDriver started successfully")
            return driver
        except Exception as e:
            logger.debug(f"  Fallback driver init: {e}")
            # Fallback without service
            return webdriver.Chrome(options=options)

    def render(self, url: str) -> tuple[Optional[str], list[str]]:
        """
        Render a page and return HTML content.

        Args:
            url: URL to render

        Returns:
            Tuple of (html_content, discovered_urls)
        """
        discovered_urls: list[str] = []

        try:
            self.driver = self._create_driver()
            self.driver.set_page_load_timeout(self.timeout)

            # Navigate to page
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)

            # Wait for body to load
            logger.info("  Waiting for page to load...")
            try:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                logger.warning("  Timeout waiting for body element")

            # Disable animations
            self._disable_animations()

            # Wait for dynamic content
            logger.info("  Waiting for dynamic content (3s)...")
            time.sleep(3)

            # Scroll to trigger lazy loading
            logger.info("  Scrolling page to trigger lazy loading...")
            discovered_urls.extend(self._scroll_page())

            # Try to expand hidden content
            logger.info("  Expanding hidden content...")
            self._expand_content()

            # Extract framework-specific resources
            logger.info("  Extracting framework resources...")
            discovered_urls.extend(self._extract_framework_resources())

            # Get final HTML
            html = self.driver.page_source
            logger.info(f"  Captured {len(html):,} bytes of HTML")
            logger.info(f"  Discovered {len(set(discovered_urls))} resource URLs")

            return html, list(set(discovered_urls))

        except TimeoutException:
            logger.error("  Page load timeout")
            return None, []
        except WebDriverException as e:
            logger.error(f"  WebDriver error: {e}")
            return None, []
        except Exception as e:
            logger.error(f"  Unexpected error: {e}")
            return None, []
        finally:
            self.close()

    def _disable_animations(self):
        """Disable CSS animations for faster rendering."""
        try:
            self.driver.execute_script("""
                var style = document.createElement('style');
                style.type = 'text/css';
                style.innerHTML = '* { animation-duration: 0.001s !important; transition-duration: 0.001s !important; }';
                document.getElementsByTagName('head')[0].appendChild(style);
            """)
            logger.debug("  Animations disabled")
        except Exception:
            pass

    def _scroll_page(self) -> list[str]:
        """Scroll through page to trigger lazy loading."""
        urls: list[str] = []

        try:
            total_height = self.driver.execute_script(
                "return Math.max("
                "document.body.scrollHeight, document.documentElement.scrollHeight, "
                "document.body.offsetHeight, document.documentElement.offsetHeight, "
                "document.body.clientHeight, document.documentElement.clientHeight);"
            )

            viewport_height = self.driver.execute_script("return window.innerHeight")
            scroll_steps = max(1, min(20, total_height // viewport_height))
            logger.debug(f"  Page height: {total_height}px, {scroll_steps} scroll steps")

            for i in range(scroll_steps + 1):
                scroll_position = (i * total_height) // scroll_steps
                self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                time.sleep(0.3)

                # Extract resources after each scroll
                try:
                    resources = self.driver.execute_script("""
                        var resources = [];
                        document.querySelectorAll('link[rel="stylesheet"], link[as="style"]').forEach(function(el) {
                            if (el.href) resources.push(el.href);
                        });
                        document.querySelectorAll('script[src]').forEach(function(el) {
                            if (el.src) resources.push(el.src);
                        });
                        document.querySelectorAll('img[src]').forEach(function(el) {
                            if (el.src && !el.src.startsWith('data:')) resources.push(el.src);
                        });
                        return resources;
                    """)
                    urls.extend(resources)
                except Exception:
                    pass

            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)

        except Exception as e:
            logger.debug(f"  Scroll error: {e}")

        return urls

    def _expand_content(self):
        """Try to click elements that might reveal more content."""
        selectors = [
            "button.load-more",
            ".show-more",
            ".expand",
            ".accordion-toggle",
            '[aria-expanded="false"]',
            ".menu-toggle",
            ".navbar-toggler",
            ".mobile-menu-button",
            ".hamburger",
            '[data-toggle="collapse"]',
        ]

        expanded_count = 0
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements[:3]:
                    if elem.is_displayed():
                        self.driver.execute_script("arguments[0].click();", elem)
                        expanded_count += 1
                        time.sleep(0.3)
            except Exception:
                continue

        if expanded_count > 0:
            logger.debug(f"  Expanded {expanded_count} elements")

    def _extract_framework_resources(self) -> list[str]:
        """Extract framework-specific resources."""
        urls: list[str] = []

        try:
            # Next.js / React resources
            next_urls = self.driver.execute_script("""
                var resources = [];
                document.querySelectorAll('script[src*="_next"]').forEach(function(el) {
                    resources.push(el.src);
                });
                document.querySelectorAll('script[src*="chunk"]').forEach(function(el) {
                    resources.push(el.src);
                });
                document.querySelectorAll('script[src*="webpack"]').forEach(function(el) {
                    resources.push(el.src);
                });
                return resources;
            """)
            urls.extend(next_urls)
            if next_urls:
                logger.debug(f"  Found {len(next_urls)} Next.js/React resources")

            # Angular resources
            angular_urls = self.driver.execute_script("""
                var resources = [];
                document.querySelectorAll('script[src*="runtime"]').forEach(function(el) {
                    resources.push(el.src);
                });
                document.querySelectorAll('script[src*="polyfills"]').forEach(function(el) {
                    resources.push(el.src);
                });
                document.querySelectorAll('script[src*="main"]').forEach(function(el) {
                    resources.push(el.src);
                });
                return resources;
            """)
            urls.extend(angular_urls)
            if angular_urls:
                logger.debug(f"  Found {len(angular_urls)} Angular resources")

        except Exception:
            pass

        return urls

    def close(self):
        """Close the WebDriver."""
        if self.driver:
            try:
                logger.debug("  Closing WebDriver...")
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def is_selenium_available() -> bool:
    """Check if Selenium is available."""
    return SELENIUM_AVAILABLE
