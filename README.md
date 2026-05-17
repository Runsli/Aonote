# PureMo-Blog

PureMo-Blog 是一个用 Python 编写的极简静态博客生成器。它把 `markdown/` 中的文章转换为纯 HTML/CSS 页面，不依赖前端框架，也不需要浏览器执行 JavaScript。

在线演示：[PureMo-Blog.vercel.app](https://PureMo-Blog.vercel.app)

## 特性

- **纯静态输出**：构建结果位于 `_site/`，可以直接部署到 Vercel、Netlify、GitHub Pages、Cloudflare Pages 等静态托管平台。
- **严格 no-JS 取向**：模板不输出可执行脚本，结构化数据使用 Microdata，部署配置中也声明了 `script-src 'none'`。
- **Markdown 写作体验**：支持 Front Matter、目录、代码高亮、表格、任务列表、提示块、删除线等常用语法。
- **SEO 与分享信息**：自动生成 `sitemap.xml`、`robots.txt`、`rss.xml`，页面包含 canonical、Open Graph、Twitter Card 与文章时间元信息。
- **无障碍与性能优化**：包含跳转主内容链接、暗色模式、减少动态效果适配、图片懒加载、异步解码、CSS 压缩与正确的 404 页面。

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
PureMo-Blog/
├── assets/
│   └── style.css              # 站点样式
├── markdown/                  # Markdown 文章和特殊页面
│   ├── 01.md
│   ├── 02.md
│   ├── 03.md
│   ├── 404.md
│   └── about.md
├── templates/
│   └── base.html              # HTML 模板
├── config.py                  # 站点与 Markdown 配置
├── parser.py                  # Markdown 解析与 HTML 后处理
├── generator.py               # 页面、RSS、Sitemap 生成逻辑
├── autobuild.py               # 构建入口
├── netlify.toml               # Netlify 构建与安全响应头
├── vercel.json                # Vercel 构建与安全响应头
└── requirements.txt
```

构建后会生成 `_site/`。该目录是构建产物，默认不需要提交到 Git。

## 写一篇文章

在 `markdown/` 目录中新建 `.md` 文件，例如 `markdown/04.md`：

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
print("Hello PureMo-Blog")
```

```python title="hello.py"
print("Hello PureMo-Blog")
```

```python title="hello.py" hl_lines="2"
message = "Hello PureMo-Blog"
print(message)
```

行内公式：$E = mc^2$

$$
\int_0^1 x^2 dx = \frac{1}{3}
$$
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

PureMo-Blog 的页面目标是作为文档存在，而不是 Web App。当前默认输出具备以下约束：

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