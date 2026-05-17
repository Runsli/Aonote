# Aonote

English | [中文](README.zh-CN.md)

Aonote is a minimal static blog generator written in Python. It turns Markdown files in `markdown/` into pure HTML/CSS pages with no frontend framework and no browser JavaScript required.

**Live demo:** [aonote.vercel.app](https://aonote.vercel.app)

## Features

Aonote is built for document-style sites and personal blogs: readable content, clear structure, easy deployment, and a good reading experience without client-side JavaScript.

### Content generation

- Reads Markdown from `markdown/` and generates post pages, home, archive, tags, about, and a real 404 page from Front Matter.
- Supports `title`, `date`, `summary`, `tags`, `hidden`, and more. Hidden pages stay out of normal post lists.
- Home shows the latest posts; archive groups by year; tags get index and detail pages automatically.
- Output goes to `_site/` for static hosting.
- Incremental builds regenerate only what changed (content, template, config, or styles).

### Markdown authoring

- Headings with anchors, auto TOC, footnotes, definition lists, task lists, admonitions, tables, strikethrough, emoji shortcodes, and math.
- Math is rendered to static MathML at build time (no runtime math engine).
- Pygments highlighting, language detection, code block titles, line highlights, and horizontal scroll for long lines.
- `diff` / `patch` blocks with added/removed line styling and screen-reader labels.
- Table captions via a line like `Table: My caption` before the table (Chinese sites may use `表格：`).
- Example posts are split by topic: basics, code/media, tables, and no-JS components.

### no-JS and interaction

- No executable JavaScript in templates; pages are documents, not web apps.
- Structured data uses Microdata instead of JSON-LD `<script>` tags.
- Mobile nav, mobile TOC, `<details>` collapses, back-to-top, and anchor jumps use native HTML/CSS.
- Deploy configs set `script-src 'none'` to reinforce the no-JS model.
- Optional empty Chrome DevTools noise file to reduce stray 404s.

### SEO, feeds, and sharing

- Generates `sitemap.xml`, `robots.txt`, `rss.xml`, and `atom.xml`.
- RSS and Atom include titles, summaries, full content, categories, author, and dates.
- Canonical URLs, Open Graph, Twitter Card, and article timestamps on pages.
- Real `_site/404.html` with `noindex` for error pages.
- `BASE_URL` and `REPO_SUBPATH` for custom domains and GitHub Pages subpaths.

### Accessibility

- Skip link, semantic nav, current page state, visible keyboard focus, and `prefers-reduced-motion` support.
- Keyboard-friendly code blocks, scrollable table regions, mobile TOC, and native collapses.
- Health checks flag missing or generic image `alt` text.
- Tables get scroll wrappers with `role="region"`, `tabindex`, and accessible names.
- Footnotes, task lists, and diff lines include screen-reader-friendly labels.
- Optional focus-order report for manual keyboard audits (`check_site.py --focus-report`).

### Visual design and performance

- Light/dark mode with GitHub Light and GitHub Dark Dimmed code themes.
- CSS variables for color, spacing, radius, shadows, focus rings, and breakpoints.
- Minified CSS with content-hashed filenames for caching.
- Optional HTML minification that preserves `pre`, `textarea`, `script`, and `style` content.
- Lazy-loaded images with async decoding and dimensions when possible.
- Consistent `scroll-margin-top` so headings are not hidden under the sticky header.

### Post-build health checks

- `autobuild.py` runs `check_site.py` after each build.
- Checks cover no-JS, links, anchors, assets, SEO, RSS/Atom, duplicate IDs, headings, tables, code blocks, footnotes, and task lists.
- Reports grouped as `A11Y`, `SEO`, `Links`, `Assets`, `Feeds`, `No-JS`, `Build`.
- Build manifest updates only after checks pass.
- Run `python check_site.py --focus-report` for per-page focus order.

## Requirements

- Python 3.7+
- pip
- Git (optional, for clone and Git-based build timestamps)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Quick start

1. Use this repo as a template, or fork/clone it.

```bash
git clone <your-repo-url>
cd <your-repo-name>
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Edit `config.py` at minimum:

```python
BASE_URL = "https://your-domain.example"
BLOG_TITLE = "Your site title"
BLOG_DESCRIPTION = "Your site description"
BLOG_AUTHOR = "Your name"
SITE_LANGUAGE = "en"  # or "zh-CN"
```

4. Build the site.

```bash
python autobuild.py
```

5. Preview locally.

```bash
cd _site
python -m http.server 8000
```

Open `http://localhost:8000`.

## Project layout

```text
Aonote/
├── assets/
│   └── style.css              # Site styles
├── static/                    # Files copied to /static/
├── markdown/                  # Posts and special pages
│   ├── welcome-to-aonote.md
│   ├── markdown-basics.md
│   ├── nojs-compliance-fixes.md
│   ├── blog-ui-ux-refactor.md
│   ├── code-and-media-examples.md
│   ├── tables-and-nojs-components.md
│   ├── 404.md
│   └── about.md
├── templates/
│   └── base.html              # HTML template
├── config.py                  # Site and Markdown settings
├── parser.py                  # Markdown parsing and HTML post-processing
├── generator.py               # Pages, RSS, sitemap
├── autobuild.py               # Build entry point
├── check_site.py              # Post-build health checks
├── i18n.py                    # UI string translations
├── netlify.toml
├── vercel.json
└── requirements.txt
```

The `_site/` directory is build output and should not be committed.

Health checks run automatically before the incremental manifest is saved. To check an existing build:

```bash
python check_site.py
python check_site.py --focus-report
```

## Write a post

Create a file under `markdown/` using lowercase kebab-case, e.g. `markdown/my-first-post.md`:

```md
---
title: My first post
date: 2026-01-01
summary: A short summary for the home page and RSS.
tags: [blog, python]
---

# My first post

Write your content in Markdown here.
```

Common Front Matter fields:

- `title` — post title.
- `slug` — optional URL slug; if omitted, derived from the filename (`my-first-post.md` → `/posts/my-first-post/`).
- `date` — publish date (`YYYY-MM-DD` recommended).
- `summary` — used on list pages, RSS, and meta description.
- `tags` — e.g. `[python, blog]`.
- `hidden: true` — exclude from normal lists (e.g. `about.md`).

Rebuild after editing:

```bash
python autobuild.py
```

## Markdown support

Built-in extensions include:

- `extra` — tables, footnotes, fenced code, etc.
- `codehilite` — Pygments highlighting.
- `toc` — table of contents and heading anchors.
- `admonition` — callout blocks.
- `sane_lists` — more predictable list parsing.
- `pymdownx.tasklist` — task lists.
- `pymdownx.tilde` — strikethrough.
- `pymdownx.emoji` — emoji shortcodes.
- `pymdownx.arithmatex` — math rendered to MathML at build time.

Example:

````md
::: warning
This is a warning callout.
:::

- [x] Done
- [ ] Todo

```python
print("Hello Aonote")
```

Inline math: $E = mc^2$

$$
\int_0^1 x^2 dx = \frac{1}{3}
$$

Table: Example caption

| Title | Status |
| :--- | :--- |
| Demo | Done |
````

## Customize the site

### Styles

Edit `assets/style.css`, then run `python autobuild.py`. CSS is minified and emitted with a content hash (e.g. `style.xxxxxxxx.css`).

### Template

Edit `templates/base.html`. Template changes trigger rebuilds of posts, home, archive, tags, RSS, and sitemap.

### Configuration

Key settings in `config.py`:

- Site: `BASE_URL`, `BLOG_TITLE`, `BLOG_DESCRIPTION`, `BLOG_AUTHOR`.
- UI language: `SITE_LANGUAGE` — strings come from `i18n.py` (`zh-CN` and `en` built in).
- Paths: `REPO_SUBPATH`, `BUILD_DIR`, `MARKDOWN_DIR`.
- Markdown: `MARKDOWN_EXTENSIONS`, `MARKDOWN_EXTENSION_CONFIGS`.
- Copyright: `COPYRIGHT_LICENSE` and defaults from `i18n.py`.

### Internationalization

- `SITE_LANGUAGE` switches **UI strings only** (navigation, buttons, copyright templates, a11y labels). It does **not** translate Markdown post bodies.
- Supported values: `zh-CN`, `en`. Add or edit keys in `i18n.py` under `TRANSLATIONS`.
- Keep the same keys in both locales, including nested keys under `copyright_license_notices`.
- Verify key parity: `python i18n.py`

## Deploy

### Vercel

`vercel.json` is included:

```json
{
  "buildCommand": "python autobuild.py",
  "outputDirectory": "_site",
  "framework": null
}
```

### Netlify

`netlify.toml` is included:

```toml
[build]
  command = "python autobuild.py"
  publish = "_site"
```

Use the real `_site/404.html` for 404s. Do not rewrite all routes to `index.html` (this is not an SPA).

### GitHub Pages

For project sites at `https://username.github.io/repo-name/`:

```python
REPO_SUBPATH = "/repo-name"
BASE_URL = "https://username.github.io/repo-name"
```

See `workflows/autobuild.yml` for an optional GitHub Actions workflow.

### After deploy

- Confirm `BASE_URL` matches production.
- Check `robots.txt`, `sitemap.xml`, links, CSS, and feeds.
- Ensure unknown URLs return 404, not the home page with 200.

## no-JS policy

Aonote targets static documents:

- No executable JavaScript in default output.
- Microdata instead of JSON-LD scripts.
- Math as static MathML at build time.
- `script-src 'none'` in security headers where configured.
- TOC, back-to-top, and mobile UI use HTML/CSS only.

Third-party analytics, comments, or embeds usually add JavaScript and may break no-JS compliance.

## FAQ

### Build fails

```bash
pip install -r requirements.txt
```

Validate YAML in Front Matter and dates as `YYYY-MM-DD`.

### Styles look stale

Run `python autobuild.py` again. Purge CDN or browser cache if the hashed CSS filename changed.

### Wrong domain in links or sitemap

```python
BASE_URL = "https://your-domain.example"
REPO_SUBPATH = ""  # or "/repo-name" for GitHub Pages project sites
```

### 404 does not work

Ensure `_site/404.html` exists and the host is not using SPA fallback to `index.html`.

## Contributing

Issues and pull requests are welcome. Please run `python autobuild.py` before submitting and verify `_site/` output.

## License

[MIT License](https://opensource.org/licenses/MIT)
