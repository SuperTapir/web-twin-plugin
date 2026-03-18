"""Command-line interface for webtwin."""

import argparse
import sys
from pathlib import Path

from . import __version__, extract_website, is_selenium_available


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="webtwin",
        description="Extract website content including HTML, CSS, JS, and images.",
    )
    parser.add_argument("url", help="URL to extract")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output path for ZIP file (default: current directory)",
    )
    parser.add_argument(
        "--no-selenium",
        action="store_true",
        help="Disable Selenium rendering",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Don't download assets, only extract metadata",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"webtwin {__version__}",
    )

    args = parser.parse_args()

    # Check Selenium availability
    use_selenium = not args.no_selenium
    if use_selenium and not is_selenium_available():
        print("Warning: Selenium not available. Using HTTP-only mode.")
        print("Install with: pip install webtwin[selenium]")
        use_selenium = False

    try:
        print(f"Extracting: {args.url}")
        print(f"Selenium: {'enabled' if use_selenium else 'disabled'}")

        result = extract_website(
            args.url,
            use_selenium=use_selenium,
            download_assets=not args.no_download,
            output_path=args.output or Path.cwd(),
            timeout=args.timeout,
        )

        print(f"\nTitle: {result.metadata.title}")
        print(f"CSS files: {len(result.assets.css)}")
        print(f"JS files: {len(result.assets.js)}")
        print(f"Images: {len(result.assets.img)}")
        print(f"Fonts: {len(result.assets.fonts)}")

        if result.output_path:
            print(f"\nSaved to: {result.output_path}")

    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
