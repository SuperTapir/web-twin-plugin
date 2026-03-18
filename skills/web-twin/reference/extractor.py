"""Main extractor for webtwin."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from urllib.parse import unquote, urlparse

from .downloader import Downloader
from .logger import logger
from .models import Assets, Components, ExtractResult
from .parser import Parser
from .renderer import SeleniumRenderer, is_selenium_available
from .utils import get_asset_type, normalize_url, resolve_url, safe_filename


def extract_website(
    url: str,
    *,
    use_selenium: bool = True,
    download_assets: bool = True,
    output_path: Optional[Union[str, Path]] = None,
    timeout: int = 30,
) -> ExtractResult:
    """
    提取网站内容，包括 HTML、静态资源和 UI 组件。

    Args:
        url: 目标网站 URL
        use_selenium: 是否使用 Selenium 渲染 JS 动态内容（默认 True）
        download_assets: 是否下载静态资源到输出目录（默认 True）
        output_path: 输出目录路径，为 None 时使用临时目录
        timeout: 请求超时时间（秒），默认 30

    Returns:
        ExtractResult 包含 HTML、资源列表、元数据和 UI 组件
    """
    # ========== 第一步：URL 标准化 ==========
    # 补全协议前缀（如 http://），统一 URL 格式
    url = normalize_url(url)
    html: Optional[str] = None
    additional_urls: list[str] = []
    final_url = url

    logger.info("=" * 60)
    logger.info(f"Extracting: {url}")
    logger.info("=" * 60)

    # ========== 第二步：获取网页 HTML ==========
    # 优先使用 Selenium 无头浏览器渲染，可执行 JS、触发懒加载
    # Selenium 会滚动页面、点击展开按钮，获取完整渲染后的 DOM
    if use_selenium and is_selenium_available():
        logger.info("Using Selenium renderer")
        try:
            with SeleniumRenderer(timeout=timeout) as renderer:
                # render() 返回: (渲染后的HTML, 滚动过程中发现的资源URL列表)
                html, additional_urls = renderer.render(url)
                if html:
                    final_url = url
        except Exception as e:
            logger.warning(f"Selenium failed: {e}")
            html = None

    # Selenium 失败时降级为普通 HTTP 请求（无法执行 JS）
    if not html:
        logger.info("Using HTTP downloader")
        with Downloader(timeout=timeout) as downloader:
            html, final_url = downloader.fetch_page(url)

    if not html:
        raise RuntimeError(f"Failed to fetch content from {url}")

    # ========== 第三步：解析 HTML ==========
    # 使用 BeautifulSoup 解析 HTML 文档
    logger.info("Parsing HTML...")
    parser = Parser(html, final_url)

    # ========== 第四步：提取元数据 ==========
    # 从 HTML 中提取: title、description、keywords、OG tags、语言、favicon 等
    logger.info("Extracting metadata...")
    metadata = parser.extract_metadata()
    logger.info(
        f"  Title: {metadata.title[:50]}..."
        if len(metadata.title) > 50
        else f"  Title: {metadata.title}"
    )

    # ========== 第五步：提取静态资源 URL ==========
    # 扫描 HTML 中的资源引用:
    # - CSS: <link rel="stylesheet">, @import
    # - JS: <script src="...">
    # - 图片: <img src/srcset/data-src>, background-image
    # - 字体: font-family 声明, .woff/.woff2 文件
    # - 视频/音频: <video>, <audio>, YouTube/Vimeo iframe
    logger.info("Extracting assets...")
    assets = parser.extract_assets()

    # ========== 第六步：提取 UI 组件 ==========
    # 根据 HTML 标签、role 属性、class 名称识别常见 UI 组件:
    # navigation, header, footer, hero, card, form, modal 等
    logger.info("Extracting UI components...")
    components = parser.extract_components()

    # ========== 第七步：合并 Selenium 发现的额外资源 ==========
    # Selenium 滚动页面时会触发懒加载，发现更多动态加载的资源
    if additional_urls:
        logger.info(f"Adding {len(additional_urls)} URLs from Selenium...")
        for asset_url in additional_urls:
            if not asset_url or asset_url.startswith("data:"):
                continue
            asset_url = resolve_url(asset_url, final_url)
            asset_type = get_asset_type(asset_url)

            if asset_type == "css" and asset_url not in assets.css:
                assets.css.append(asset_url)
            elif asset_type == "js" and asset_url not in assets.js:
                assets.js.append(asset_url)
            elif asset_type == "img" and asset_url not in assets.img:
                assets.img.append(asset_url)
            elif asset_type == "fonts" and asset_url not in assets.fonts:
                assets.fonts.append(asset_url)

    # ========== 第八步：正则补充提取 ==========
    # 如果提取到的资源太少（<10个），用正则扫描原始 HTML 补充遗漏的资源
    total_assets = len(assets.css) + len(assets.js) + len(assets.img)
    if total_assets < 10:
        logger.info("Few assets found, scanning for additional patterns...")
        parser.extract_additional_assets_from_patterns(assets)

    # 输出资源统计
    logger.info("Asset summary:")
    logger.info(f"  CSS:    {len(assets.css)} files")
    logger.info(f"  JS:     {len(assets.js)} files")
    logger.info(f"  Images: {len(assets.img)} files")
    logger.info(f"  Fonts:  {len(assets.fonts)} files")

    # ========== 第九步：修复相对 URL ==========
    # 将 HTML 中的相对路径转为绝对路径，确保离线浏览时资源能正确加载
    # 例如: /images/logo.png -> https://example.com/images/logo.png
    logger.info("Fixing relative URLs...")
    fixed_html = parser.fix_relative_urls()

    # ========== 第十步：构建结果对象 ==========
    result = ExtractResult(
        url=final_url,
        html=fixed_html,
        assets=assets,
        metadata=metadata,
        components=components,
    )

    # ========== 第十一步：保存到输出目录 ==========
    # 下载所有静态资源，按类型分目录保存，生成可离线浏览的网站副本
    if download_assets:
        logger.info("Saving to output directory...")
        output_dir = _save_to_directory(result, output_path, timeout)
        result.output_path = output_dir
        logger.info(f"Saved to: {output_dir}")

    logger.info("=" * 60)
    logger.info("Extraction complete!")
    logger.info("=" * 60)

    return result


def _save_to_directory(
    result: ExtractResult,
    output_path: Optional[Union[str, Path]],
    timeout: int,
) -> Path:
    """
    将提取的内容保存到目录。

    输出目录结构:
    output_dir/
    ├── index.html      # 主 HTML 文件（相对路径已转为绝对路径）
    ├── metadata.json   # 网站元数据（title, description, og_tags 等）
    ├── README.md       # 自动生成的说明文档
    ├── css/            # 样式表文件
    │   └── fonts.css   # Google Fonts 导入（如有）
    ├── js/             # JavaScript 文件
    ├── img/            # 图片文件
    ├── fonts/          # 字体文件
    └── components/     # 提取的 UI 组件
        ├── index.html  # 组件预览页
        └── {type}/     # 按类型分目录存放
    """
    # 确定输出目录路径
    if output_path:
        output_dir = Path(output_path)
    else:
        # 未指定时使用临时目录: /tmp/webtwin/{domain}_{timestamp}/
        domain = safe_filename(urlparse(result.url).netloc)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = Path(tempfile.gettempdir()) / "webtwin"
        output_dir = temp_dir / f"{domain}_{timestamp}"

    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)

    with Downloader(timeout=timeout) as downloader:
        # 保存主 HTML 文件
        (output_dir / "index.html").write_text(result.html, encoding="utf-8")
        logger.debug("  Added index.html")

        # 下载并保存所有静态资源（CSS、JS、图片、字体等）
        _save_assets_to_directory(output_dir, result.assets, result.url, downloader)

        # 保存元数据 JSON
        metadata_json = json.dumps(
            result.metadata.__dict__, indent=2, ensure_ascii=False
        )
        (output_dir / "metadata.json").write_text(metadata_json, encoding="utf-8")
        logger.debug("  Added metadata.json")

        # 保存 UI 组件（如果有）
        if result.components.to_dict():
            _save_components_to_directory(output_dir, result.components)

        # 生成 Google Fonts 导入文件（根据页面中使用的字体族）
        if result.assets.font_families:
            fonts_css = "\n".join(
                f"/* Font Family: {family} */\n"
                f"@import url('https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}&display=swap');\n"
                for family in result.assets.font_families
            )
            css_dir = output_dir / "css"
            css_dir.mkdir(exist_ok=True)
            (css_dir / "fonts.css").write_text(fonts_css, encoding="utf-8")

        # 生成 README 说明文档
        readme = _generate_readme(result)
        (output_dir / "README.md").write_text(readme, encoding="utf-8")

    return output_dir


def _save_assets_to_directory(
    output_dir: Path,
    assets: Assets,
    base_url: str,
    downloader: Downloader,
):
    """
    下载静态资源并保存到对应目录。

    处理流程:
    1. 按资源类型（css/js/img/fonts 等）分别创建子目录
    2. 遍历每个资源 URL，下载内容
    3. 根据 URL 路径生成文件名，处理重名和特殊字符
    4. 记录下载成功/失败统计
    """
    # 资源类型与对应 URL 列表的映射
    asset_types = {
        "css": assets.css,
        "js": assets.js,
        "img": assets.img,
        "fonts": assets.fonts,
        "videos": assets.videos,
        "audio": assets.audio,
        "favicons": assets.favicons,
    }

    for asset_type, urls in asset_types.items():
        if not urls:
            continue

        logger.info(f"  Downloading {len(urls)} {asset_type} files...")

        # 创建资源类型对应的子目录
        asset_dir = output_dir / asset_type
        asset_dir.mkdir(exist_ok=True)

        processed = set()  # 已处理的 URL，避免重复下载
        success_count = 0
        failures: list[tuple[str, str]] = []  # (文件名, 失败原因)

        for idx, url in enumerate(urls):
            # 跳过空 URL、data: URI 和已处理的 URL
            if not url or url.startswith("data:") or url in processed:
                continue
            processed.add(url)

            try:
                # 从 URL 路径中提取文件名
                parsed = urlparse(url)
                filename = os.path.basename(unquote(parsed.path))
                if not filename:
                    filename = f"asset_{len(processed)}.{asset_type}"
                elif "." not in filename:
                    filename = f"{filename}.{asset_type}"

                # 如果 URL 带查询参数，添加哈希后缀避免文件名冲突
                # 例如: style.css?v=123 -> style_v_123.css
                if parsed.query:
                    query_hash = safe_filename(parsed.query)[:20]
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{query_hash}{ext}"

                # 下载资源内容
                content, error = downloader.download_asset_with_reason(url, base_url)
                if content:
                    (asset_dir / filename).write_bytes(content)
                    success_count += 1
                else:
                    failures.append((filename, error or "Unknown error"))
            except Exception as e:
                failures.append((url.split("/")[-1][:30], str(e)))
                continue

        # 输出下载统计
        if success_count == len(urls):
            logger.info(f"    Downloaded {success_count}/{len(urls)} successfully")
        else:
            logger.info(f"    Downloaded {success_count}/{len(urls)} successfully")
            for filename, reason in failures:
                logger.warning(f"      Failed: {filename} - {reason}")


def _save_components_to_directory(output_dir: Path, components: Components):
    """
    保存提取的 UI 组件到目录。

    生成内容:
    - components/index.html: 组件预览页，展示所有组件及其源码
    - components/{type}/component_{n}.html: 各类型组件的独立 HTML 文件
    """
    import html as html_lib

    components_dir = output_dir / "components"
    components_dir.mkdir(exist_ok=True)

    # 创建组件预览页的 HTML 头部
    index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Extracted UI Components</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .component { margin-bottom: 40px; border: 1px solid #ddd; border-radius: 5px; overflow: hidden; }
        .component-header { background: #f5f5f5; padding: 10px 15px; border-bottom: 1px solid #ddd; }
        .component-content { padding: 15px; }
        .component-code { background: #f8f8f8; padding: 15px; border-top: 1px solid #ddd; white-space: pre-wrap; overflow-x: auto; }
        h1, h2 { color: #333; }
        pre { margin: 0; }
    </style>
</head>
<body>
    <h1>Extracted UI Components</h1>
"""

    components_dict = components.to_dict()
    component_count = sum(len(v) for v in components_dict.values())
    logger.info(f"  Adding {component_count} UI components...")

    for comp_type, comp_list in components_dict.items():
        if not comp_list:
            continue

        index_html += f"<h2>{comp_type.replace('_', ' ').title()} Components</h2>\n"
        comp_type_dir = components_dir / comp_type
        comp_type_dir.mkdir(exist_ok=True)

        for i, comp in enumerate(comp_list):
            html_code = comp.get("html", "")
            if not html_code:
                continue

            # Add to index
            index_html += f"""
<div class="component">
    <div class="component-header">
        <strong>{comp_type.replace("_", " ").title()} {i + 1}</strong>
    </div>
    <div class="component-content">
        {html_code}
    </div>
    <div class="component-code">
        <pre>{html_lib.escape(html_code)}</pre>
    </div>
</div>
"""
            # Save individual component
            (comp_type_dir / f"component_{i + 1}.html").write_text(
                html_code, encoding="utf-8"
            )

    index_html += """
</body>
</html>
"""
    (components_dir / "index.html").write_text(index_html, encoding="utf-8")


def _generate_readme(result: ExtractResult) -> str:
    """
    生成 README.md 说明文档。

    包含: 目录结构说明、元数据摘要、使用方法、注意事项等。
    """
    domain = urlparse(result.url).netloc
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""# Website Clone: {domain}

Extracted on: {timestamp}
Source URL: {result.url}

## Contents

- `index.html`: Main HTML file
- `css/`: Stylesheets ({len(result.assets.css)} files)
- `js/`: JavaScript files ({len(result.assets.js)} files)
- `img/`: Images ({len(result.assets.img)} files)
- `fonts/`: Font files ({len(result.assets.fonts)} files)
- `components/`: Extracted UI components
- `metadata.json`: Website metadata

## Metadata

- **Title**: {result.metadata.title}
- **Description**: {result.metadata.description[:100]}{"..." if len(result.metadata.description) > 100 else ""}
- **Language**: {result.metadata.language}

## How to Use

1. Open `index.html` in your browser
2. For best results, serve with a local server:
   ```
   python -m http.server 8000
   ```
   Then open http://localhost:8000

## Components

View extracted UI components by opening `components/index.html`

## Notes

- Some assets may not load due to CORS restrictions
- External APIs and dynamic content may not work
- JavaScript functionality may be limited

---
Generated by webtwin
"""
