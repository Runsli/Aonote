---
title: Aonote 青笺
date: 2026-05-20
summary: 用 Python 将 Markdown 生成为纯 HTML/CSS 的 no-JS 静态博客生成器。本站即官方站点与可运行演示。
tags: [项目]
---

# Aonote 青笺

**Aonote 青笺** 是一个用 Python 编写的 no-JS 静态博客生成器。它把 `markdown/` 里的文章转成可直接部署的 HTML/CSS 页面：不依赖前端框架，也不要求浏览器执行 JavaScript。

本站 [aonote.vercel.app](https://aonote.vercel.app) 同时承担 **项目官网** 与 **在线演示**——你正在阅读的页面，就是用它自己构建出来的。

## 为什么做它

- **内容站应该是文档，不是 Web App**：阅读、订阅、搜索索引不应绑定客户端运行时。
- **构建期完成重活**：代码高亮、数学公式（MathML）、目录与 SEO 元信息在构建时生成。
- **默认可检查**：`check_site.py` 在构建后检查链接、no-JS、无障碍与订阅源，减少上线后的隐性问题。

## 快速开始

```bash
git clone https://github.com/Runsli/Aonote.git
cd Aonote
pip install -r requirements.txt
```

编辑 `config.py` 中的 `BASE_URL`、`BLOG_TITLE`、`BLOG_AUTHOR`，替换 `markdown/` 里的欢迎文与关于页，然后：

```bash
python autobuild.py
cd _site && python -m http.server 8000
```

更完整的步骤见 [快速开始](/posts/doc-quickstart/)。

## 核心能力

- 首页、文章、归档、标签、关于页与真实 404。
- Markdown 扩展：代码高亮、目录、表格、脚注、任务列表、提示块、数学公式等。
- RSS、Atom、Sitemap、Open Graph；结构化数据使用 Microdata，无 JSON-LD `<script>`。
- 浅色/暗色模式、移动端导航、键盘焦点与 `prefers-reduced-motion`。
- 增量构建与构建后健康检查。

## 链接

- **源码与 Issue**：[github.com/Runsli/Aonote](https://github.com/Runsli/Aonote)
- **项目生态**（Aonote / Astro 主题 / 个人站）：[doc-ecosystem](/posts/doc-ecosystem/)
- **Astro 主题（可选 JS）**：[astro-theme-aonote](https://github.com/runsli/astro-theme-aonote) · [在线演示](https://astro-theme-aonote.vercel.app)
- **作者**：[Runsli 的小站](https://www.runsli.com/)
- **关于本项目**：[关于页](/about/)
- **更新日志**：[changelog](/posts/doc-changelog/)
- **Markdown 渲染预览**：[Markdown 排版示例](/posts/markdown-basics/)

## 命名

`Aonote` 保留 note（笔记）的含义；中文名 **青笺** 强调纸页与安静书写。少一点运行时，多一点内容本身。

---

若你 Fork 本仓库做自己的博客，请阅读仓库 [README](https://github.com/Runsli/Aonote/blob/main/README.zh-CN.md#fork-后定制自己的站点) 中的「Fork 后定制」一节。
