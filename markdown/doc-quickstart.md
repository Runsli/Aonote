---
title: 快速开始
date: 2026-05-18
summary: 从克隆仓库到本地预览与部署 Aonote 站点的最短路径。
tags: [文档]
---

# 快速开始

本文介绍如何把 Aonote 跑起来，并部署到你自己的域名。若你只想浏览功能，可直接看 [首页](/posts/welcome-to-aonote/) 与 [Markdown 排版示例](/posts/markdown-basics/)。

## 环境要求

- Python 3.7+
- pip
- Git（可选，用于克隆与构建时间戳）

## 1. 获取代码

```bash
git clone https://github.com/Runsli/Aonote.git
cd Aonote
pip install -r requirements.txt
```

也可在 GitHub 上使用 **Use this template** 创建你自己的仓库。

## 2. 配置站点

编辑 `config.py`，至少修改以下项：

```python
BASE_URL = "https://your-domain.example"
BLOG_TITLE = "你的站点标题"
BLOG_DESCRIPTION = "你的站点描述"
BLOG_AUTHOR = "你的名字"
SITE_LANGUAGE = "zh-CN"  # 或 "en"
```

若部署在 GitHub Pages 子路径（如 `username.github.io/repo-name/`），还需设置 `REPO_SUBPATH`。

## 3. 准备内容

在 `markdown/` 中写作。Front Matter 示例：

```yaml
---
title: 我的第一篇文章
date: 2026-05-20
summary: 显示在首页与 RSS 中的摘要。
tags: [blog]
---

正文从这里开始。
```

特殊文件：

- `about.md`：关于页（建议 `hidden: true`）。
- `404.md`：404 页面内容。

## 4. 构建与预览

```bash
python autobuild.py
cd _site
python -m http.server 8000
```

浏览器打开 `http://localhost:8000`。构建通过后会更新 `_site/`，并在健康检查通过后写入增量构建清单。

单独运行检查：

```bash
python check_site.py
```

## 5. 部署

将 `_site/` 目录发布到任意静态托管即可，例如：

- **Vercel / Netlify**：连接仓库，构建命令 `python autobuild.py`，发布目录 `_site`（仓库已含 `vercel.json` / `netlify.toml`）。
- **GitHub Pages**：将 `_site` 内容推送到 `gh-pages` 分支，或使用 Actions 构建。

部署后确认 `BASE_URL` 与线上域名一致，否则 canonical、RSS 与 Sitemap 中的链接会不正确。

## Fork 官方站内容时

若你 Fork 的是包含本官网内容的仓库，请按 [关于页 · Fork 做自己的站](/about/) 替换欢迎文、关于页，并删除不需要的 `doc-*.md` 项目文档。

## 下一步

- [为什么坚持 no-JS](/posts/doc-why-no-js/)
- [项目仓库](https://github.com/Runsli/Aonote)
- [完整 README](https://github.com/Runsli/Aonote/blob/main/README.zh-CN.md)
