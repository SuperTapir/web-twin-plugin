# web-twin

[English](./README.md) | 简体中文

Claude Code 插件：网站提取、克隆与资源抓取。

> 基于 [WebTwin](https://github.com/sirioberati/WebTwin) by [Sirio Berati](https://stan.store/heysirio) ([@heysirio](https://github.com/sirioberati))，MIT 协议。

## 它能做什么

安装后，当你让 Claude 克隆或提取网站时，Claude 会自动获得 `web_twin` 模块的完整知识：

- 如何调用 `extract_website()` 抓取网站的 HTML、CSS、JS、图片、字体
- 如何提取 UI 组件（导航栏、卡片、表单等 13 种类型）
- 如何处理 JavaScript 渲染的页面（Selenium 无头浏览器）
- 异步调用、反检测、多级降级等最佳实践

**你不需要手动做任何事**——安装插件后直接对 Claude 说"帮我克隆这个网站"就行。

## 安装

### 方式 A：Marketplace（推荐）

```bash
claude plugin marketplace add SuperTapir/web-twin-plugin
claude plugin install web-twin@web-twin-plugin
```

### 方式 B：Git Clone

```bash
git clone https://github.com/SuperTapir/web-twin-plugin.git
cp -r web-twin-plugin/skills/web-twin ~/.claude/skills/web-twin
```

这会将 skill 复制到用户级 skills 目录（`~/.claude/skills/`），所有项目都可以使用。

也可以加载整个插件用于本地开发：

```bash
claude --plugin-dir ./web-twin-plugin
```

### 开始使用

```
> 帮我提取 https://example.com 的网站资源和 UI 组件

> 用 web_twin 抓取这个页面，分析它的布局结构

> 克隆这个网站的设计，提取所有 CSS 和图片
```

## 触发短语

当你的对话中提到以下内容时，Skill 会自动激活：

| 场景 | 触发词 |
|------|--------|
| 网站克隆 | "clone site", "克隆网站", "extract website" |
| 资源抓取 | "scrape", "crawl page", "download page" |
| 组件提取 | "UI components", "提取组件" |
| 模块调用 | "web_twin", "webtwin", "extract_website" |
| 工作流 | "url2app", "website to app" |

## 核心能力

```
Selenium 无头浏览器渲染（JS 动态内容）
  ↓ 失败则降级
HTTP 静态下载
  ↓ 产出 HTML
BeautifulSoup 解析
  ↓ 资源太少
正则补充扫描
```

- **11 步提取流水线**：URL 标准化 → 渲染 → 解析 → 元数据/资源/组件提取 → 输出
- **反检测**：User-Agent 轮换、Referer 随机化、重试机制
- **框架感知**：Next.js / React / Angular 专属资源提取
- **13 种 UI 组件**：navigation, header, footer, hero, card, form, CTA, sidebar, modal, section, store, mobile, cart

## 插件内容

```
web-twin-plugin/
├── .claude-plugin/plugin.json       # 插件清单
├── LICENSE                          # MIT 协议
├── README.md                        # English
├── README.zh-CN.md                  # 中文文档
└── skills/web-twin/
    ├── SKILL.md                     # Skill 文档（Claude 自动读取）
    └── reference/                   # 完整模块源码
        ├── __init__.py              # 公共 API
        ├── extractor.py             # 主提取器（11 步流水线）
        ├── parser.py                # HTML/CSS 解析
        ├── renderer.py              # Selenium 渲染
        ├── downloader.py            # HTTP 下载（反检测）
        ├── models.py                # 数据模型
        ├── utils.py                 # 工具函数
        ├── logger.py                # 日志
        ├── cli.py                   # CLI 接口
        └── requirements.txt         # Python 依赖
```

## Credits

基于 [WebTwin](https://github.com/sirioberati/WebTwin) by **Sirio Berati**。

- 原始仓库：https://github.com/sirioberati/WebTwin
- 作者主页：https://stan.store/heysirio

## License

MIT — 详见 [LICENSE](./LICENSE)。
