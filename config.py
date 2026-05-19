# config.py / 站点配置文件

import os
from pymdownx import emoji

# --- 站点配置 / Site configuration ---
# 这里主要是配置站点信息，如标题、描述、作者、CSS 文件名、Markdown 扩展列表、Markdown 扩展配置、列表配置、目录和文件配置、特殊文件名称等。
# Main site settings: title, description, author, CSS filename, Markdown extensions, paths, and special filenames.

# 博客的根 URL，也就是外部直接访问的站点的链接
# Public site root URL used in canonical links, feeds, and sitemap.

# 当你部署在 GitHub Pages, Netlify 或者 Vercel 这样的平台，你需要修改 BASE_URL 配置项为对应的链接
# When deploying to GitHub Pages, Netlify, or Vercel, set BASE_URL to your production domain.
# 当你在设置了自定义域名的时候，你也需要修改 BASE_URL 配置项为对应的链接
# If you use a custom domain, update BASE_URL to match it.
# 也就是最终的访问链接
# This should be the final URL visitors use.

BASE_URL = "https://aonote.vercel.app"

# 假设你的网站部署在 GitHub Pages 且不是 username.github.io 的链接
# If the site is served from a GitHub Pages project path instead of a user site,
# 而是 https://username.github.io/your-repo-name/
# for example https://username.github.io/your-repo-name/,
# 这种情况下，你要修改下面的这个 REPO_SUBPATH 配置项为对应的 子目录路径
# set REPO_SUBPATH to that subdirectory.
# 请将 "/your-repo-name" 替换为你实际的子目录路径或 GitHub 仓库名，填写在下方
# Replace "/your-repo-name" with your actual repository subpath below.

REPO_SUBPATH = ""

# 内部链接的根路径 / Internal path prefix for generated links
SITE_ROOT = REPO_SUBPATH.rstrip('/')

# 这里是博客的标题、描述、作者 / Blog title, description, and author

# 这里是网站的标题 / Site title shown in header and metadata
BLOG_TITLE = "Aonote 青笺"

# 描述，通常作为描述信息在搜索引擎的结果页面或者社交链接分享的时候链接中显示
# Site description used in search results and social sharing metadata.
BLOG_DESCRIPTION = "用 Python 编写的 no-JS 静态博客生成器：Markdown 进，纯 HTML/CSS 出，无需浏览器端 JavaScript。"
# 作者，主要作用于网站页脚的位置进行显示
# Author name shown in the footer and feed metadata.
BLOG_AUTHOR = "Runsli"

# 首页浏览器标签与分享标题（不在页面正文中显示）/ Homepage <title> and social cards only
INDEX_PAGE_TITLE = "Aonote 青笺"
INDEX_PAGE_SUBTITLE = "no-JS 静态博客生成器"

# 页脚 GitHub 仓库链接，留空则不显示 / GitHub repo URL in footer; empty to hide
GITHUB_REPO_URL = "https://github.com/Runsli/Aonote"

# 站点界面语言。可选值参考 i18n.py，例如 "zh-CN" 或 "en"。
# UI language for fixed template strings. See i18n.py. Supported: "zh-CN", "en".
SITE_LANGUAGE = "zh-CN"

# 存储 CSS 文件的哈希名 / Source CSS filename before content-hash renaming
CSS_FILENAME = 'style.css'

# 是否在生成 HTML 页面时移除模板缩进和多余标签间空白。
# Whether to minify generated HTML by removing template indentation and extra whitespace.
# 会保留 pre/textarea/script/style 中的原始内容，避免影响代码块显示。
# Raw blocks inside pre/textarea/script/style are preserved for code blocks.
HTML_MINIFY = True

# 定义代码高亮使用的 CSS 类名 / CSS class name used for Pygments code blocks
CODE_HIGHLIGHT_CLASS = 'highlight'

# 页脚内容配置 - 可选值: 'build_time', 'empty', 'custom'
# Footer content type: build timestamp, empty, or custom text.
FOOTER_CONTENT_TYPE = 'custom'  # 默认显示构建时间 / Show build time by default
FOOTER_CUSTOM_TEXT = 'Aonote 青笺 · no-JS 静态站'  # 自定义文本内容 / Custom footer text

# config.py 中添加完整的版权配置 / Copyright notice configuration
# --- 版权声明配置 / Copyright license settings ---
COPYRIGHT_LICENSE = {
    'enable': True,  # 是否启用版权申明 / Enable copyright notice on posts
    'type': 'CC_BY_NC_SA_4.0',  # 许可协议类型 / License type key
    'custom_text': '',  # 自定义版权文本，当 type 为 CUSTOM 时使用 / Custom text when type is CUSTOM
    'show_license_icon': True,  # 是否显示许可协议图标 / Show license icon badge
    'show_standard_format': True,  # 是否显示标准格式 / Show standard attribution block
    'additional_note': '',  # 留空时使用 i18n.py 中的默认附加说明 / Empty uses i18n default note
    'format_template': '',  # 留空时使用 i18n.py 中的默认引用格式 / Empty uses i18n default format
    'allowed_types': {
        # Creative Commons 许可证 / Creative Commons licenses
        'CC_BY_4.0': {
            'icon': '<i title="Creative Commons Attribution">CC-BY</i>'
        },
        'CC_BY_SA_4.0': {
            'icon': '<i title="Creative Commons Attribution ShareAlike">CC-BY-SA</i>'
        },
        'CC_BY_NC_4.0': {
            'icon': '<i title="Creative Commons Attribution NonCommercial">CC-BY-NC</i>'
        },
        'CC_BY_NC_SA_4.0': {
            'icon': '<i title="Creative Commons Attribution NonCommercial ShareAlike">CC-BY-NC-SA</i>'
        },
        'CC_BY_NC_ND_4.0': {
            'icon': '<i title="Creative Commons Attribution NonCommercial NoDerivatives">CC-BY-NC-ND</i>'
        },
        'CC_BY_ND_4.0': {
            'icon': '<i title="Creative Commons Attribution NoDerivatives">CC-BY-ND</i>'
        },
        'CC_ZERO_1.0': {
            'icon': '<i title="Creative Commons Zero">CC0</i>'
        },

        # 开源软件许可证 / Open-source software licenses
        'MIT': {
            'icon': '<i title="MIT License">MIT</i>'
        },
        'BSD_2_CLAUSE': {
            'icon': '<i title="BSD 2-Clause License">BSD-2</i>'
        },
        'BSD_3_CLAUSE': {
            'icon': '<i title="BSD 3-Clause License">BSD-3</i>'
        },
        'APACHE_2.0': {
            'icon': '<i title="Apache License 2.0">Apache-2.0</i>'
        },
        'GPL_2.0': {
            'icon': '<i title="GNU General Public License v2.0">GPL-2.0</i>'
        },
        'GPL_3.0': {
            'icon': '<i title="GNU General Public License v3.0">GPL-3.0</i>'
        },
        'LGPL_2.1': {
            'icon': '<i title="GNU Lesser General Public License v2.1">LGPL-2.1</i>'
        },
        'LGPL_3.0': {
            'icon': '<i title="GNU Lesser General Public License v3.0">LGPL-3.0</i>'
        },
        'MPL_2.0': {
            'icon': '<i title="Mozilla Public License 2.0">MPL-2.0</i>'
        },
        'EPL_2.0': {
            'icon': '<i title="Eclipse Public License 2.0">EPL-2.0</i>'
        },

        # 其他常见许可证 / Other common licenses
        'UNLICENSE': {
            'icon': '<i title="The Unlicense">Unlicense</i>'
        },
        'WTFPL': {
            'icon': '<i title="Do What The F*ck You Want To Public License">WTFPL</i>'
        },
        'AGPL_3.0': {
            'icon': '<i title="GNU Affero General Public License v3.0">AGPL-3.0</i>'
        },

        # 自定义许可证 / Custom license placeholder
        'CUSTOM': {
            'icon': '<i title="Custom License">Custom</i>'
        }
    }
}
# --- Markdown 配置 / Markdown configuration ---
# 1. 扩展列表 (使用短名称) / Extension list (short names)
MARKDOWN_EXTENSIONS = [
    'extra',              # 包含 fenced_code (```), tables, footnotes / Fenced code, tables, footnotes
    'codehilite',         # 代码高亮 (必须安装 Pygments) / Syntax highlighting (requires Pygments)
    'toc',                # 目录 / Table of contents
    'admonition',         # 提示块 / Admonition callouts
    'sane_lists',         # 更好的列表 / Improved list parsing
    'pymdownx.tasklist',  # 任务列表支持 (- [ ]) / Task lists
    'pymdownx.tilde',     # [新增] 删除线支持 (~~text~~) / Strikethrough
    'pymdownx.emoji',     # Emoji 短代码支持 (:wink:) / Emoji shortcodes
    'pymdownx.arithmatex', # 数学公式支持 ($...$ / $$...$$) / Math to MathML
]

# 2. 扩展具体配置 / Per-extension settings
MARKDOWN_EXTENSION_CONFIGS = {
    'toc': {
        'baselevel': 2,
        'anchorlink': True,
    },
    'codehilite': {
        'linenums': False,
        'css_class': CODE_HIGHLIGHT_CLASS, # 强制指定类名为 'highlight' / Force highlight class name
        'use_pygments': True,          # 强制使用 Pygments / Always use Pygments
        'noclasses': False,            # 使用 CSS 类而非内联样式 / Use CSS classes, not inline styles
        'guess_lang': True,            # 自动猜测语言 / Guess code language
    },
    'pymdownx.tasklist': {
        'custom_checkbox': True,      # 允许使用 CSS 自定义样式 / Custom checkbox styling
        'clickable_checkbox': False,  # 静态页面通常设为不可点击 / Non-interactive in static output
    },
    'pymdownx.emoji': {
        'emoji_index': emoji.gemoji,
        'emoji_generator': emoji.to_alt,
    },
    'pymdownx.arithmatex': {
        'generic': True,
    },
}
# --- Markdown 配置结束 / End of Markdown configuration ---


# --- 列表配置 / List page settings ---
MAX_POSTS_ON_INDEX = 5

# --- 目录和文件配置 / Directory and file paths ---
MARKDOWN_DIR = 'markdown'
BUILD_DIR = '_site'
POSTS_DIR_NAME = 'posts'
TAGS_DIR_NAME = 'tags'
STATIC_DIR = 'static'
MEDIA_DIR = 'media'

ABOUT_PAGE = 'about.md'

# 特殊文件名称 / Special generated filenames
SITEMAP_FILE = 'sitemap.xml'
RSS_FILE = 'rss.xml'
ATOM_FILE = 'atom.xml'
ARCHIVE_FILE = 'archive.html'
TAGS_LIST_FILE = 'tags.html'
