---
title: 关于 Aonote 青笺
date: 2026-05-20
summary: Aonote 青笺的设计原则、功能边界、作者信息与仓库链接。
hidden: true
---

# 关于 Aonote 青笺

Aonote 青笺是一个面向个人博客、技术笔记与轻量文档站的 **no-JS 静态站生成器**。它关注内容长期可读、页面结构清晰、构建产物易于部署，并在不依赖浏览器端 JavaScript 的前提下保留足够的阅读与无障碍体验。

## 设计原则

- **内容优先**：布局服务于标题、正文、代码与表格，而不是炫技式交互。
- **纯静态输出**：构建结果是 HTML、CSS 与静态资源；关键体验不绑定客户端脚本。
- **构建期增强**：高亮、公式、目录、订阅源与大部分 SEO 在 Python 构建阶段完成。
- **默认可检查**：`autobuild.py` 结束后运行 `check_site.py`，覆盖链接、no-JS、无障碍与 Feeds。
- **容易迁移**：文章在 Markdown，样式在 CSS，无 lock-in 式前端运行时。

## 作者

本站由 [Runsli](https://www.runsli.com/) 创建并维护。个人博客记录学习、项目与对极简 Web 的实践；Aonote 是其中一个开源项目。

- 个人站：[www.runsli.com](https://www.runsli.com/)
- 项目仓库：[github.com/Runsli/Aonote](https://github.com/Runsli/Aonote)

欢迎通过 GitHub Issue 反馈问题或提交 Pull Request。

## 相关项目：Astro 主题

若你需要在**保持 Aonote 阅读体验与内容模型**的前提下，用客户端 JavaScript 实现更复杂的交互（例如组件化 UI、渐进增强、与 Astro 生态集成），可以使用同系列的 **[astro-theme-aonote](https://github.com/runsli/astro-theme-aonote)**：

| | [Aonote 青笺](https://github.com/Runsli/Aonote)（本仓库） | [astro-theme-aonote](https://github.com/runsli/astro-theme-aonote) |
| --- | --- | --- |
| 技术栈 | Python 构建，纯 HTML/CSS | Astro 5，可按需加 JS |
| 定位 | no-JS 文档站、极简部署、构建期检查 | 同款版式与 Markdown 能力的 Astro 移植 |
| 演示 | [aonote.vercel.app](https://aonote.vercel.app) | [astro-theme-aonote.vercel.app](https://astro-theme-aonote.vercel.app) |

两个项目**互相独立维护**，样式与信息架构尽量对齐，便于在「极简 no-JS」与「可扩展交互」之间切换，而不是二选一的对立关系。

## 许可

项目源码遵循仓库中的 [LICENSE](https://github.com/Runsli/Aonote/blob/main/LICENSE)。本站文章默认采用 CC BY-NC-SA 4.0（见各文末尾版权块）。

## Fork 做自己的站

本仓库默认 `markdown/` 内容面向 **Aonote 官网**。若你 Fork 后想改成个人博客，通常只需：

1. 修改 `config.py` 中的站点信息与 `BASE_URL`。
2. 替换 `welcome-to-aonote.md` 与 `about.md`。
3. 删除以 `doc-` 开头的项目文档（若不需要）。
4. 保留或删除 `markdown-basics.md` 等示例文。
5. 运行 `python autobuild.py` 并部署 `_site/`。

详细说明见 [README · Fork 后定制](https://github.com/Runsli/Aonote/blob/main/README.zh-CN.md#fork-后定制自己的站点)。
