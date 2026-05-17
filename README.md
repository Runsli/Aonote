# Aonote 青笺

Aonote 青笺是一个用 Python 编写的极简静态博客生成器。它把 `markdown/` 中的文章转换为纯 HTML/CSS 页面，不依赖前端框架，也不需要浏览器执行 JavaScript。

在线演示：[aonote.vercel.app](https://aonote.vercel.app)

## 功能概览

Aonote 青笺的定位是一个偏文档、偏博客的 no-JS 静态站生成器。它关注内容长期可读、页面结构清晰、构建结果容易部署，以及在不依赖浏览器端 JavaScript 的前提下保留足够好的阅读体验。

### 内容生成

- 从 `markdown/` 读取 Markdown 文件，并根据 Front Matter 生成文章页、首页、归档页、标签页、关于页和 404 页面。
- 支持 `title`、`date`、`summary`、`tags`、`hidden` 等常用元信息，隐藏页面不会进入普通文章列表。
- 首页按发布时间展示最新文章，归档页按年份组织文章，标签页自动生成标签索引和标签详情页。
- 构建产物输出到 `_site/`，可以直接作为静态目录部署。
- 支持增量构建，只有内容、模板、配置或样式变化时才重新生成必要页面。

### Markdown 写作

- 支持标题锚点、自动目录、脚注、定义列表、任务列表、提示块、表格、删除线、Emoji 短代码和数学公式。
- 数学公式在构建期转为静态 MathML，不需要前端脚本渲染。
- 支持 Pygments 代码高亮、代码块语言识别、代码块标题、指定行高亮和长代码行横向滚动。
- 支持 `diff` / `patch` 代码块的加减行高亮，并为新增行、删除行补充屏幕阅读器标签。
- 支持表格标题语法，例如 `表格：示例说明`，构建时会生成语义化 `<caption>`。
- 示例文档已按主题拆分为基础排版、代码与媒体、表格与 no-JS 组件，便于查看实际渲染效果。

### no-JS 与交互

- 模板默认不输出可执行 JavaScript，页面目标是文档而不是 Web App。
- 结构化数据使用 Microdata，避免 JSON-LD `<script>`。
- 移动端导航、移动端目录、折叠内容、返回顶部、锚点跳转等交互均使用 HTML/CSS 原生能力。
- 部署配置中设置了 `script-src 'none'`，帮助保持 no-JS 约束。
- 自动生成空的 Chrome DevTools 噪音文件，减少无关 404 请求干扰。

### SEO、订阅与分享

- 自动生成 `sitemap.xml`、`robots.txt`、`rss.xml` 和 `atom.xml`。
- RSS 和 Atom 包含文章标题、摘要、正文内容、分类标签、作者、发布时间和更新时间。
- 页面自动输出 canonical、Open Graph、Twitter Card、文章发布时间和修改时间等元信息。
- 404 页面使用真实 `_site/404.html`，并配置 `noindex`，避免错误页面被搜索引擎收录。
- 支持 `BASE_URL` 和 `REPO_SUBPATH`，适配自定义域名、根路径部署和 GitHub Pages 子路径部署。

### 无障碍

- 页面包含跳转主内容链接、语义化导航、当前页面状态、可见键盘焦点和 `prefers-reduced-motion` 适配。
- 代码块、表格横向滚动区域、移动端目录和原生折叠块均考虑键盘访问。
- 图片会检查缺失或过于泛化的 `alt` 文本。
- 表格滚动容器会补充 `role="region"`、`tabindex` 和可访问名称。
- 脚注引用、脚注返回链接、任务列表状态、diff 行语义均补充了屏幕阅读器友好的标签。
- 健康检查可以输出焦点顺序报告，辅助人工检查键盘导航体验。

### 视觉与性能

- 内置浅色/暗色模式，代码高亮使用 GitHub Light 与 GitHub Dark Dimmed 风格。
- CSS 使用变量组织颜色、间距、圆角、阴影、焦点样式和响应式断点。
- 构建时压缩 CSS，并生成带内容哈希的 CSS 文件名，方便长期缓存。
- HTML 可选压缩，会保留 `pre`、`textarea`、`script`、`style` 等对空白敏感的内容。
- 图片默认补充懒加载、异步解码和尺寸信息，减少布局偏移。
- 锚点跳转使用统一的 `scroll-margin-top`，避免标题被顶部栏遮挡。

### 构建健康检查

- `autobuild.py` 构建结束后会自动运行 `check_site.py`。
- 检查项覆盖 no-JS、站内链接、锚点、图片资源、基础 SEO、RSS/Atom、重复 ID、标题层级、表格、代码块、脚注和任务列表。
- 报告按 `A11Y`、`SEO`、`Links`、`Assets`、`Feeds`、`No-JS`、`Build` 分类展示。
- 构建清单只会在健康检查通过后更新，避免失败构建污染增量构建状态。
- 可以单独运行 `python check_site.py --focus-report` 输出每个页面的可聚焦元素顺序。

## 环境要求

- Python 3.7+
- pip
- Git（可选，用于克隆仓库和获取文章构建时间）

安装依赖：

```bash
pip install -r requirements.txt
```

## 快速开始

1. 使用模板创建新仓库，或 Fork/Clone 本仓库。

```bash
git clone <your-repo-url>
cd <your-repo-name>
```

2. 安装依赖。

```bash
pip install -r requirements.txt
```

3. 编辑 `config.py`，至少确认以下配置：

```python
BASE_URL = "https://your-domain.example"
BLOG_TITLE = "你的站点标题"
BLOG_DESCRIPTION = "你的站点描述"
BLOG_AUTHOR = "你的名字"
SITE_LANGUAGE = "zh-CN"
```

4. 构建站点。

```bash
python autobuild.py
```

5. 本地预览。

```bash
cd _site
python -m http.server 8000
```

然后访问 `http://localhost:8000`。

## 目录结构

```text
Aonote/
├── assets/
│   └── style.css              # 站点样式
├── static/                    # 直接复制到站点根路径 /static/ 的静态资源
├── markdown/                  # Markdown 文章和特殊页面
│   ├── welcome-to-aonote.md
│   ├── markdown-basics.md
│   ├── nojs-compliance-fixes.md
│   ├── blog-ui-ux-refactor.md
│   ├── code-and-media-examples.md
│   ├── tables-and-nojs-components.md
│   ├── 404.md
│   └── about.md
├── templates/
│   └── base.html              # HTML 模板
├── config.py                  # 站点与 Markdown 配置
├── parser.py                  # Markdown 解析与 HTML 后处理
├── generator.py               # 页面、RSS、Sitemap 生成逻辑
├── autobuild.py               # 构建入口
├── check_site.py              # 构建后健康检查
├── netlify.toml               # Netlify 构建与安全响应头
├── vercel.json                # Vercel 构建与安全响应头
└── requirements.txt
```

构建后会生成 `_site/`。该目录是构建产物，默认不需要提交到 Git。

构建脚本会在写入增量构建清单前自动运行健康检查；如需单独检查已有构建产物，可以运行：

```bash
python check_site.py
```

需要人工走查键盘顺序时，可以额外输出每个页面的可聚焦元素顺序：

```bash
python check_site.py --focus-report
```

## 写一篇文章

在 `markdown/` 目录中新建 `.md` 文件，文件名建议使用小写 kebab-case，例如 `markdown/my-first-post.md`：

```md
---
title: 我的第一篇文章
date: 2026-01-01
summary: 这是一段显示在首页和 RSS 中的摘要。
tags: [blog, python]
---

# 我的第一篇文章

这里是正文内容。你可以使用 Markdown 语法写作。
```

常用 Front Matter：

- `title`：文章标题。
- `slug`：可选的文章 URL 标识；如果省略，会从文件名推导，例如 `my-first-post.md` 会生成 `/posts/my-first-post/`。
- `date`：发布日期，格式建议为 `YYYY-MM-DD`。
- `summary`：文章摘要，会用于列表页、RSS 和页面描述。
- `tags`：标签列表，例如 `[python, blog]`。
- `hidden: true`：隐藏文章，不进入普通博客列表，适合 `about.md` 等特殊页面。

写完后重新构建：

```bash
python autobuild.py
```

## Markdown 支持

默认启用的扩展包括：

- `extra`：表格、脚注、围栏代码块等。
- `codehilite`：Pygments 代码高亮。
- `toc`：自动目录与标题锚点。
- `admonition`：提示块。
- `sane_lists`：更稳定的列表解析。
- `pymdownx.tasklist`：任务列表。
- `pymdownx.tilde`：删除线。
- `pymdownx.emoji`：Emoji 短代码；常见简写表情如 `:)`、`8-)` 会自动转为 emoji。
- `pymdownx.arithmatex`：数学公式，构建期渲染为静态 MathML。

示例：

````md
::: warning
这里是一段提示信息。
:::

- [x] 已完成
- [ ] 未完成

```python
print("Hello Aonote")
```

```python title="hello.py"
print("Hello Aonote")
```

```python title="hello.py" hl_lines="2"
message = "Hello Aonote"
print(message)
```

行内公式：$E = mc^2$

$$
\int_0^1 x^2 dx = \frac{1}{3}
$$

表格：示例表格说明

| 标题 | 状态 |
| :--- | :--- |
| 示例 | 已完成 |
````

## 修改站点

### 修改样式

编辑 `assets/style.css`，然后重新运行：

```bash
python autobuild.py
```

构建脚本会压缩 CSS，并生成带内容哈希的文件名，例如 `style.xxxxxxxx.css`。

### 修改模板

编辑 `templates/base.html`，然后重新构建。模板变更会触发文章页、首页、归档页、标签页、RSS 和 Sitemap 重新生成。

### 修改配置

主要配置集中在 `config.py`：

- 站点信息：`BASE_URL`、`BLOG_TITLE`、`BLOG_DESCRIPTION`、`BLOG_AUTHOR`。
- 界面语言：`SITE_LANGUAGE`，固定 UI 文案来自 `i18n.py`，当前内置 `zh-CN` 和 `en`。
- 路径配置：`REPO_SUBPATH`、`BUILD_DIR`、`MARKDOWN_DIR`。
- Markdown 扩展：`MARKDOWN_EXTENSIONS`、`MARKDOWN_EXTENSION_CONFIGS`。
- 版权信息：`COPYRIGHT_LICENSE` 控制开关、类型和图标；默认版权文案来自 `i18n.py`。

## 部署

### Vercel

仓库已包含 `vercel.json`：

```json
{
  "buildCommand": "python autobuild.py",
  "outputDirectory": "_site",
  "framework": null
}
```

导入仓库后，Vercel 会自动运行构建命令并发布 `_site/`。

### Netlify

仓库已包含 `netlify.toml`：

```toml
[build]
  command = "python autobuild.py"
  publish = "_site"
```

Netlify 会自动使用 `_site/404.html` 作为真实 404 页面。不要把所有路径重写到 `index.html`，静态博客不需要 SPA 回退规则。

### 部署后检查

- `config.py` 中的 `BASE_URL` 是否为线上实际域名。
- `robots.txt` 和 `sitemap.xml` 是否使用正确域名。
- 文章链接、CSS、RSS 是否能正常访问。
- 错误路径是否返回 404，而不是首页 200。

## no-JS 说明

Aonote 青笺的页面目标是作为文档存在，而不是 Web App。当前默认输出具备以下约束：

- 不输出可执行 JavaScript。
- 结构化数据使用 Microdata，而不是 JSON-LD `<script>`。
- 数学公式在构建期渲染为静态 MathML，不需要浏览器端脚本。
- 安全响应头包含 `script-src 'none'`。
- 目录、返回顶部、移动端目录等交互均使用 HTML/CSS 原生能力。

如果你添加第三方统计、评论、搜索或嵌入组件，请注意它们通常会引入 JavaScript，这可能破坏 no-JS 合规性。

## 常见问题

### 构建失败

先确认依赖已安装：

```bash
pip install -r requirements.txt
```

然后检查 Markdown Front Matter 是否为合法 YAML，日期是否为 `YYYY-MM-DD` 格式。

### 样式没有更新

重新运行：

```bash
python autobuild.py
```

构建脚本会为 CSS 生成新的哈希文件名。如果线上仍旧显示旧样式，通常是 CDN 或浏览器缓存导致。

### 线上链接或 Sitemap 域名不对

检查 `config.py`：

```python
BASE_URL = "https://your-domain.example"
REPO_SUBPATH = ""
```

如果部署在 GitHub Pages 的子路径，例如 `https://username.github.io/repo-name/`，需要设置：

```python
REPO_SUBPATH = "/repo-name"
```

### 404 页面不生效

确认 `_site/404.html` 存在，并且部署平台没有配置 `/* -> /index.html` 的 SPA 回退规则。

## 贡献

欢迎提交 Issue 或 Pull Request。建议在提交前运行：

```bash
python autobuild.py
```

并检查生成后的 `_site/` 页面是否符合预期。

## 许可协议

本项目使用 [MIT License](https://opensource.org/licenses/MIT)。