---
title: 为什么坚持 no-JS
date: 2026-05-17
summary: Aonote 将页面视为文档而非应用：无客户端脚本、构建期增强与可检查性。
tags: [文档]
---

# 为什么坚持 no-JS

Aonote 的目标用户写的是**文章、笔记与文档**，不是需要复杂客户端状态的应用。因此默认输出不包含可执行的浏览器 JavaScript。

## 页面是文档

博客与知识库的核心体验是：阅读、跳转、订阅、被搜索引擎索引。这些都不应依赖：

- 客户端路由与 hydration
- 运行时 Markdown 或数学渲染
- 用脚本补上的导航、目录或主题切换

Aonote 把代码高亮、公式（MathML）、目录锚点、Open Graph 等放在 **构建阶段** 完成，部署后只有 HTML 与 CSS。

## 结构化数据不用 `<script>`

许多站点用 JSON-LD 的 `<script type="application/ld+json">` 做结构化数据。Aonote 改用 **Microdata** 写在 HTML 元素上，避免在页面里出现 script 标签，也更贴近 [nojs.club](https://nojs.club/) 所倡导的精神。

## 交互用 HTML/CSS 原生能力

这些能力不依赖脚本：

- 移动端导航（`:target` / checkbox hack 等纯 CSS 方案）
- `<details>` / `<summary>` 折叠
- 返回顶部（锚点链接）
- 浅色/暗色模式（`prefers-color-scheme` 与 CSS 变量）

## 可验证

`check_site.py` 会检查：

- 是否存在不应出现的可执行脚本
- 链接、锚点、图片与 Feeds 是否有效
- 基础无障碍与 SEO 细节

构建失败时不会更新增量清单，避免「坏构建」被当成已发布状态。

## 不是反对一切 JS

no-JS 指的是 **你的读者不必为你的内容站加载脚本**。构建工具本身用 Python，与浏览器无关。若你将来需要个别页面的例外，应在明确约束下审慎添加，并仍通过健康检查把关。

## 相关阅读

- [快速开始](/posts/doc-quickstart/)
- [首页 · Aonote 是什么](/posts/welcome-to-aonote/)
- [nojs.club](https://nojs.club/)
