---
title: 项目生态
date: 2026-05-20
summary: Aonote 青笺、astro-theme-aonote 与 Runsli 小站的关系说明，以及如何选择与互链。
tags: [文档]
---

# 项目生态

**Aonote 青笺** 不是孤立仓库：它与同系列的 Astro 主题、作者个人站一起构成一套「同款阅读体验、不同技术约束」的选择。本文是**完整版说明**；其它仓库 README 与 Astro 主题文档会链到此处，避免多处维护同一张大表。

## 三个入口分别是什么

表格：Aonote 系列三个入口

| 入口 | 链接 | 角色 |
| --- | --- | --- |
| **Aonote 青笺**（本仓库） | [github.com/Runsli/Aonote](https://github.com/Runsli/Aonote) · [aonote.vercel.app](https://aonote.vercel.app) | Python 构建的 no-JS 静态博客生成器；本页所在**项目官网** |
| **astro-theme-aonote** | [github.com/runsli/astro-theme-aonote](https://github.com/runsli/astro-theme-aonote) · [astro-theme-aonote.vercel.app](https://astro-theme-aonote.vercel.app) | 同款版式与内容模型的 **Astro 5 移植**；可按需加客户端 JS |
| **Runsli 的小站** | [www.runsli.com](https://www.runsli.com/) | 作者个人博客（note / jotting），**不是** Aonote 产品文档站 |

三者**独立部署、独立维护**，但在视觉与 Markdown 能力上尽量对齐，方便你在不同场景切换。

## 如何选择

```text
需要零浏览器 JS、Python 构建、check_site 质检、申 nojs / 体积类 Club？
  → Aonote 青笺（本仓库）

需要 Astro 生态、组件化、客户端增强或 npm 模板一键建站？
  → astro-theme-aonote

想了解作者、阅读建站随笔（与产品文档无关的个人内容）？
  → runsli.com
```

不必二选一：有人用 Aonote 做生产博客，用 Astro 主题做实验站；也有人从 Python 版迁到 Astro 版以扩展交互。

## 技术对照

表格：Aonote 与 Astro 主题技术对照

| 维度 | Aonote 青笺 | astro-theme-aonote |
| --- | --- | --- |
| 运行时 | 构建期 Python；页面无必需 JS | Node 构建；页面可按需含 JS |
| 内容目录 | `markdown/` | `src/content/posts/` |
| 站点配置 | `config.py` | `src/site.config.ts` |
| 布局模板 | `templates/base.html` | `src/layouts/BaseLayout.astro` |
| 样式 | `assets/style.css` | `src/styles/aonote.css` |
| 界面文案 | `i18n.py` | `src/i18n.ts` |
| 构建产物 | `_site/` | `dist/` |
| 构建命令 | `python autobuild.py` | `npm run build` |
| 特色 | `check_site.py`、增量构建、no-JS 约束 | Astro 集成、Shiki、模板 `npm create astro` |

更细的 upstream mapping 见 [astro-theme-aonote README](https://github.com/runsli/astro-theme-aonote#upstream-mapping)。

## 与 Runsli 小站的关系

[runsli.com](https://www.runsli.com/) 使用 **Thought Lite** 系 Astro 主题（与 Aonote 产品线不同），主要发个人笔记与建站日志。其中与 Aonote 相关的文章会链回本官网与 GitHub，例如：

- [Aonote 近期更新](https://www.runsli.com/note/260518)（建站日志）
- [项目生态说明（个人站短文）](https://www.runsli.com/note/260520)（链回本页）

产品选型、配置对照、Fork 说明请以**本官网文档**为准；个人站文章偏经历与回顾，可能滞后于仓库最新 commit。

## 许可与反馈

- Aonote 与 astro-theme-aonote 源码许可见各自仓库 `LICENSE`（均为 MIT）。
- 问题与 PR：各仓库 GitHub Issues；Aonote 也可在 [关于页](/about/) 查看作者联系方式。

## 相关阅读

- [快速开始](/posts/doc-quickstart/)
- [为什么坚持 no-JS](/posts/doc-why-no-js/)
- [更新日志](/posts/doc-changelog/)
- [关于 Aonote](/about/)
