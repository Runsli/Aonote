# 解析器模块 / Parser module script

import os
import re
import yaml
import json
import markdown
from datetime import datetime, date
from typing import Dict, Any, Tuple, Optional, List
import config 
import unicodedata 
from bs4 import BeautifulSoup, NavigableString  # 引入 BeautifulSoup / Import BeautifulSoup
from i18n import get_translations
from latex2mathml.converter import convert as convert_latex_to_mathml


def _get_i18n() -> Dict[str, Any]:
    return get_translations(getattr(config, 'SITE_LANGUAGE', 'zh-CN'))


def _prepend_hidden_label(soup: BeautifulSoup, element, label: str) -> None:
    if element.find(class_='diff-line-label'):
        return
    hidden_label = soup.new_tag('span', attrs={'class': 'diff-line-label visually-hidden'})
    hidden_label.string = label
    element.insert(0, hidden_label)


def _add_diff_line_semantics(soup: BeautifulSoup, pre, i18n: Dict[str, Any]) -> None:
    added_label = i18n.get('diff_added_line_label', 'Added line: ')
    removed_label = i18n.get('diff_removed_line_label', 'Removed line: ')
    for added_line in pre.select('.gi'):
        _prepend_hidden_label(soup, added_line, added_label)
    for removed_line in pre.select('.gd'):
        _prepend_hidden_label(soup, removed_line, removed_label)


def _extract_table_caption(table) -> Optional[str]:
    sibling = table.previous_sibling
    while isinstance(sibling, NavigableString) and not sibling.strip():
        sibling = sibling.previous_sibling

    if not sibling or getattr(sibling, 'name', None) != 'p':
        return None

    text = sibling.get_text(" ", strip=True)
    for prefix in ('表格：', '表：', 'Table: ', 'Table：', 'Caption: ', 'Caption：'):
        if text.startswith(prefix):
            caption = text[len(prefix):].strip()
            if caption:
                sibling.decompose()
                return caption
    return None


def _build_table_caption(soup: BeautifulSoup, caption_text: str, i18n: Dict[str, Any]):
    caption_tag = soup.new_tag('caption')
    prefix = soup.new_tag('span', attrs={'class': 'table-caption-prefix', 'aria-hidden': 'true'})
    prefix.string = i18n.get('table_caption_prefix', 'Table: ')
    caption_tag.append(prefix)
    caption_tag.append(caption_text)
    return caption_tag


def _footnote_number_from_link(link) -> str:
    text = link.get_text(" ", strip=True)
    if text:
        return text.strip("[]")
    href = link.get('href', '')
    match = re.search(r'(?:fn|fnref):([^#]+)$', href)
    return match.group(1) if match else ''


def _footnote_number_from_backref(soup: BeautifulSoup, backref) -> str:
    href = backref.get('href', '')
    if not href.startswith('#'):
        return _footnote_number_from_link(backref)

    target = soup.find(id=href[1:])
    if target:
        ref_link = target.find('a', class_='footnote-ref')
        if ref_link:
            return _footnote_number_from_link(ref_link)
    return _footnote_number_from_link(backref)


def _add_footnote_semantics(soup: BeautifulSoup, i18n: Dict[str, Any]) -> None:
    ref_template = i18n.get('footnote_ref_label', 'Footnote {number}')
    backref_template = i18n.get('footnote_backref_label', 'Back to footnote {number} reference')

    for ref_link in soup.select('a.footnote-ref'):
        number = _footnote_number_from_link(ref_link)
        label = ref_template.format(number=number)
        ref_link['aria-label'] = label
        ref_link['title'] = label

    for backref in soup.select('a.footnote-backref'):
        number = _footnote_number_from_backref(soup, backref)
        label = backref_template.format(number=number)
        backref['aria-label'] = label
        backref['title'] = label


def _add_task_list_semantics(soup: BeautifulSoup, i18n: Dict[str, Any]) -> None:
    completed_template = i18n.get('task_completed_label', 'Completed task: {task}')
    incomplete_template = i18n.get('task_incomplete_label', 'Incomplete task: {task}')
    completed_state = i18n.get('task_completed_state', 'Completed')
    incomplete_state = i18n.get('task_incomplete_state', 'Incomplete')

    for item in soup.select('li.task-list-item'):
        checkbox = item.find('input', attrs={'type': 'checkbox'})
        if not checkbox:
            continue

        task_text = " ".join(item.get_text(" ", strip=True).split())
        is_completed = checkbox.has_attr('checked')
        label = completed_template.format(task=task_text) if is_completed else incomplete_template.format(task=task_text)
        checkbox['aria-label'] = label
        checkbox['aria-disabled'] = 'true'
        item['data-task-state'] = 'completed' if is_completed else 'incomplete'

        if not item.find(class_='task-state-label'):
            state_label = soup.new_tag('span', attrs={'class': 'task-state-label visually-hidden'})
            state_label.string = f"{completed_state if is_completed else incomplete_state}: "
            control = item.find(class_='task-list-control')
            if control:
                control.insert_after(state_label)
            else:
                item.insert(0, state_label)


def _read_image_dimensions(image_path: str) -> Optional[Tuple[int, int]]:
    """使用标准库读取常见图片格式的宽高信息，从而为懒加载图片补充尺寸以避免布局偏移（CLS）。

Read common raster image dimensions with the Python standard library so lazy-loaded images can include width and height hints and avoid cumulative layout shift.
"""
    try:
        with open(image_path, 'rb') as f:
            header = f.read(32)

            if header.startswith(b'\x89PNG\r\n\x1a\n') and len(header) >= 24:
                return int.from_bytes(header[16:20], 'big'), int.from_bytes(header[20:24], 'big')

            if header[:6] in (b'GIF87a', b'GIF89a') and len(header) >= 10:
                return int.from_bytes(header[6:8], 'little'), int.from_bytes(header[8:10], 'little')

            if header.startswith(b'\xff\xd8'):
                f.seek(2)
                while True:
                    marker_start = f.read(1)
                    if not marker_start:
                        return None
                    if marker_start != b'\xff':
                        continue

                    marker = f.read(1)
                    while marker == b'\xff':
                        marker = f.read(1)
                    if not marker:
                        return None

                    if marker in (b'\xc0', b'\xc1', b'\xc2', b'\xc3', b'\xc5', b'\xc6', b'\xc7', b'\xc9', b'\xca', b'\xcb', b'\xcd', b'\xce', b'\xcf'):
                        segment = f.read(7)
                        if len(segment) < 7:
                            return None
                        return int.from_bytes(segment[5:7], 'big'), int.from_bytes(segment[3:5], 'big')

                    length_bytes = f.read(2)
                    if len(length_bytes) < 2:
                        return None
                    segment_length = int.from_bytes(length_bytes, 'big')
                    if segment_length < 2:
                        return None
                    f.seek(segment_length - 2, os.SEEK_CUR)
    except OSError:
        return None

    return None


def _resolve_local_image_path(src: str, md_file_path: str) -> Optional[str]:
    """根据 Markdown 源文件位置，将图片 ``src`` 解析为可用的本地磁盘路径；外部 URL、协议相对或 data URL 不处理。

Resolve a Markdown ``img`` ``src`` to a local filesystem path relative to the project or the Markdown file; remote URLs, protocol-relative URLs, and ``data:`` payloads are skipped.
"""
    if not src or src.startswith(('http://', 'https://', '//', 'data:')):
        return None

    project_root = os.path.dirname(__file__)
    if src.startswith('/'):
        candidate = os.path.join(project_root, src.lstrip('/'))
    else:
        candidate = os.path.join(os.path.dirname(md_file_path), src)

    return candidate if os.path.isfile(candidate) else None


def _convert_colon_admonitions(markdown_text: str) -> str:
    """将 VuePress / VitePress 风格的 ``::: type`` 围栏提示块改写为兼容 Python Markdown 的 ``!!!`` 语法。

Normalize colon-fenced VuePress/VitePress admonitions (``::: tip`` / ``::: note`` fences) into the ``!!! kind`` directive form expected by Markdown extensions downstream.
"""
    fence_re = re.compile(r'^(\s*):{3,}\s*([A-Za-z0-9_-]+)?(?:\s+(.*?))?\s*$')
    close_re = re.compile(r'^\s*:{3,}\s*$')
    lines = markdown_text.splitlines()
    converted = []
    i = 0

    while i < len(lines):
        start_match = fence_re.match(lines[i])
        if not start_match or close_re.match(lines[i]):
            converted.append(lines[i])
            i += 1
            continue

        indent, kind, title = start_match.groups()
        kind = (kind or 'note').lower()
        body = []
        i += 1

        while i < len(lines) and not close_re.match(lines[i]):
            body.append(lines[i])
            i += 1

        if i >= len(lines):
            converted.append(start_match.group(0))
            converted.extend(body)
            continue

        admonition_title = f' "{title.strip()}"' if title and title.strip() else ''
        converted.append(f'{indent}!!! {kind}{admonition_title}')
        if body:
            for body_line in body:
                converted.append(f'{indent}    {body_line}' if body_line.strip() else '')
        else:
            converted.append('')
        i += 1

    return '\n'.join(converted) + ('\n' if markdown_text.endswith('\n') else '')


EMOTICON_EMOJI_MAP = {
    '8-)': '😎',
    ':-)': '🙂',
    ':)': '🙂',
    ':-(': '☹️',
    ':(': '☹️',
    ':-*': '😘',
    ':*': '😘',
    r':\*': '😘',
    ';)': '😉',
}

EMOTICON_RE = re.compile(
    r'(?<![\w/])(?P<emoticon>8-\)|:-\)|:\)|:-\(|:\(|:-\*|:\*|:\\\*|;\))(?![\w])'
)


def _convert_emoticon_shorthands(markdown_text: str) -> str:
    """把常见 ASCII 颜文字改写为 emoji，跳过围栏代码块与行内代码，避免误替换。

Replace ASCII emoticon shorthand (``:)``, ``:(``, etc.) with emoji equivalents while respecting fenced blocks and inline backtick spans so literals stay untouched.
"""
    fence_re = re.compile(r'^\s*(`{3,}|~{3,})')
    inline_code_re = re.compile(r'(`+)(.*?)(?<!`)\1')
    lines = markdown_text.splitlines(keepends=True)
    converted = []
    in_fence = False
    fence_marker = ''

    def replace_plain_text(text: str) -> str:
        return EMOTICON_RE.sub(lambda match: EMOTICON_EMOJI_MAP[match.group('emoticon')], text)

    def replace_outside_inline_code(line: str) -> str:
        parts = []
        last_end = 0
        for match in inline_code_re.finditer(line):
            parts.append(replace_plain_text(line[last_end:match.start()]))
            parts.append(match.group(0))
            last_end = match.end()
        parts.append(replace_plain_text(line[last_end:]))
        return ''.join(parts)

    for line in lines:
        fence_match = fence_re.match(line)
        if fence_match:
            marker = fence_match.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ''
            converted.append(line)
            continue

        converted.append(line if in_fence else replace_outside_inline_code(line))

    return ''.join(converted)


def _normalize_fenced_code_attributes(markdown_text: str) -> str:
    """支持形如 `` ```python title="file.py"`` 的围栏属性写法，并整理为 Markdown 插件可识别的表单（含 hl_lines 展开）。

Accept human-friendly fenced code attributes—language plus ``title=`` hints and comma/range ``hl_lines``—then normalize markers so later highlighters/extensions parse them reliably.
"""
    opening_re = re.compile(r'^(?P<indent>\s*)(?P<fence>`{3,}|~{3,})(?P<info>[^\n]*)$')
    title_re = re.compile(r'''(?:^|\s)title=(?:"[^"]*"|'[^']*'|[^\s}]+)''')
    hl_lines_re = re.compile(r'''hl_lines=(?:"([^"]*)"|'([^']*)'|([^\s}]+))''')
    lines = markdown_text.splitlines(keepends=True)
    converted = []
    in_fence = False
    fence_marker = ''
    fence_length = 0

    def expand_hl_lines(match: re.Match) -> str:
        value = next((group for group in match.groups() if group is not None), '')
        expanded = []
        for token in re.split(r'[\s,]+', value.strip()):
            if not token:
                continue
            range_match = re.fullmatch(r'(\d+)-(\d+)', token)
            if range_match:
                start, end = map(int, range_match.groups())
                if start <= end:
                    expanded.extend(str(line_no) for line_no in range(start, end + 1))
                else:
                    expanded.extend(str(line_no) for line_no in range(start, end - 1, -1))
            elif token.isdigit():
                expanded.append(token)

        return f'hl_lines="{" ".join(dict.fromkeys(expanded))}"'

    for line in lines:
        line_body = line.rstrip('\r\n')
        line_break = line[len(line_body):]
        fence_match = opening_re.match(line_body)

        if fence_match:
            fence = fence_match.group('fence')
            info = fence_match.group('info').strip()
            marker = fence[0]

            if not in_fence:
                in_fence = True
                fence_marker = marker
                fence_length = len(fence)
                info = hl_lines_re.sub(expand_hl_lines, info)

                if 'title=' in info:
                    if info.startswith('{') and info.endswith('}'):
                        normalized_info = title_re.sub('', info).replace('{ ', '{').strip()
                        normalized_info = re.sub(r'\s+', ' ', normalized_info)
                        line = f'{fence_match.group("indent")}{fence} {normalized_info}{line_break}'
                    elif not info.startswith('{'):
                        parts = info.split(maxsplit=1)
                        language = parts[0] if parts else ''
                        attributes = parts[1] if len(parts) > 1 else ''
                        attributes = title_re.sub('', attributes).strip()
                        if language:
                            normalized_language = language.removeprefix('.')
                            attribute_suffix = f' {attributes}' if attributes else ''
                            line = f'{fence_match.group("indent")}{fence} {{.{normalized_language}{attribute_suffix}}}{line_break}'
            elif marker == fence_marker and len(fence) >= fence_length and not info:
                in_fence = False
                fence_marker = ''
                fence_length = 0

        converted.append(line)

    return ''.join(converted)


def _normalize_code_text(code: str) -> str:
    """统一代码文本的行尾格式与首尾换行，使 Markdown 源与浏览器 DOM 中提取的片段可以稳定比对。

Normalize newline characters and stray leading/trailing blank lines inside fence bodies so hashed comparisons between source Markdown and rendered ``<pre>`` text stay stable.
"""
    return code.replace('\r\n', '\n').replace('\r', '\n').strip('\n')


def _render_mathml(soup: BeautifulSoup) -> None:
    """把 arithmatex 留下的 TeX 容器节点离线转换为静态 MathML 并挂载回 DOM。

Replace Arithmatex-produced TeX-bearing nodes with statically generated MathML using ``latex2mathml``, preserving inline vs display modes inferred from wrappers.
"""
    for math_node in soup.select('.arithmatex'):
        raw_text = math_node.get_text().strip()
        display_mode = math_node.name == 'div' or raw_text.startswith('\\[') or raw_text.startswith('$$')

        if raw_text.startswith('\\(') and raw_text.endswith('\\)'):
            latex = raw_text[2:-2].strip()
        elif raw_text.startswith('\\[') and raw_text.endswith('\\]'):
            latex = raw_text[2:-2].strip()
        elif raw_text.startswith('$$') and raw_text.endswith('$$'):
            latex = raw_text[2:-2].strip()
        else:
            latex = raw_text

        if not latex:
            continue

        try:
            mathml = convert_latex_to_mathml(latex)
        except Exception:
            continue

        mathml_soup = BeautifulSoup(mathml, 'html.parser')
        math_tag = mathml_soup.find('math')
        if not math_tag:
            continue

        math_tag['display'] = 'block' if display_mode else 'inline'
        math_node.clear()
        math_node.append(math_tag)


def _normalize_language_label(language: str) -> str:
    """将以类名形式出现的别名规范成用于 UI 徽章的大写缩写标签。

Map shorthand lexer/class tokens (``.py``, ``tsx``, shell variants, etc.) to compact uppercase badges shown on code fences.
"""
    normalized = language.strip().lower()
    normalized = normalized.removeprefix('language-').removeprefix('.')

    aliases = {
        'py': 'PYTHON',
        'python': 'PYTHON',
        'python3': 'PYTHON',
        'js': 'JS',
        'javascript': 'JS',
        'ts': 'TS',
        'typescript': 'TS',
        'sh': 'SHELL',
        'shell': 'SHELL',
        'bash': 'SHELL',
        'zsh': 'SHELL',
        'html': 'HTML',
        'xml': 'XML',
        'css': 'CSS',
        'scss': 'SCSS',
        'json': 'JSON',
        'yaml': 'YAML',
        'yml': 'YAML',
        'md': 'MD',
        'markdown': 'MD',
        'diff': 'DIFF',
        'patch': 'DIFF',
        'sql': 'SQL',
        'txt': 'TEXT',
        'text': 'TEXT',
    }

    return aliases.get(normalized, re.sub(r'[^a-z0-9#+-]+', '-', normalized).strip('-').upper())


def _language_from_fence_info(info: str) -> Optional[str]:
    """从围栏首行的 info（语言与属性串联）中提取语言标识字符串。

Extract the lexer/language token from a fenced-code info line, stripping attr-list braces when present.
"""
    first_token = info.strip().split(maxsplit=1)[0] if info.strip() else ''
    if not first_token:
        return None

    # 支持 `{.python}` 等 Python-Markdown attr_list class 写法 / Respect attr-list class shorthand like `{.python}`
    attr_match = re.search(r'\.([A-Za-z0-9_+#-]+)', first_token)
    if attr_match:
        first_token = attr_match.group(1)

    label = _normalize_language_label(first_token)
    return label or None


def _title_from_fence_info(info: str) -> Optional[str]:
    """从围栏首行 info（语言与属性的串联片段）中提取 ``title`` 属性的可读标题。

Pull the optional human-facing ``title=`` caption from an info line when authors annotate fenced snippets.
"""
    match = re.search(r'''(?:^|\s)title=(?:"([^"]*)"|'([^']*)'|([^\s]+))''', info)
    if not match:
        return None

    title = next((group for group in match.groups() if group is not None), '').strip()
    return title or None


def _extract_fenced_code_blocks(markdown_text: str) -> List[Dict[str, Optional[str]]]:
    """扫描 Markdown 原文中的围栏片段，并把声明的语言/标题回填到稍后渲染完成的 ``<pre>`` 结构中。

Enumerate fenced code regions from the untouched Markdown payload so downstream HTML augmentation can annotate ``language`` and ``title`` metadata.
"""
    pattern = re.compile(
        r'^(?P<fence>`{3,}|~{3,})[ \t]*(?P<info>[^\n]*)\n(?P<code>.*?)(?:\n(?P=fence)[ \t]*)$',
        re.MULTILINE | re.DOTALL,
    )
    blocks = []

    for match in pattern.finditer(markdown_text):
        info = match.group('info')
        blocks.append({
            'language': _language_from_fence_info(info),
            'title': _title_from_fence_info(info),
            'code': _normalize_code_text(match.group('code')),
            'used': False,
        })

    return blocks


def _guess_language_label(code: str) -> Optional[str]:
    """当作者省略语言注解时，用启发式规则和 Pygments 猜测最合适的高亮标签。

Best-effort language detection using lightweight heuristics first, falling back to ``pygments.lexers.guess_lexer`` when available.
"""
    stripped_code = code.strip()
    if not stripped_code:
        return None

    if stripped_code.startswith('<') and '>' in stripped_code:
        return 'HTML'

    try:
        json.loads(stripped_code)
        return 'JSON'
    except json.JSONDecodeError:
        pass

    if re.search(r'(^|\n)\s*(def|class)\s+\w+|(^|\n)\s*(from\s+\w+\s+import|import\s+\w+)|print\s*\(', stripped_code):
        return 'PYTHON'

    if re.search(r'\b(console\.log|function\s+\w*|const\s+\w+|let\s+\w+|var\s+\w+|=>)\b', stripped_code):
        return 'JS'

    if re.search(r'\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|CREATE TABLE|ALTER TABLE)\b', stripped_code, re.IGNORECASE):
        return 'SQL'

    if '{' in stripped_code and '}' in stripped_code and re.search(r'[\w-]+\s*:\s*[^;{}]+;', stripped_code):
        return 'CSS'

    if re.search(r'(^|\n)\s*(#!\/|npm\s+|pnpm\s+|yarn\s+|cd\s+|mkdir\s+|python3?\s+|git\s+)', stripped_code):
        return 'SHELL'

    if re.search(r'(^|\n)\s*(#{1,6}\s+|[-*+]\s+|>\s+)|```', stripped_code):
        return 'MD'

    try:
        from pygments.lexers import guess_lexer
        from pygments.util import ClassNotFound
    except ImportError:
        return None

    try:
        lexer = guess_lexer(code)
    except ClassNotFound:
        return None

    aliases = getattr(lexer, 'aliases', None) or []
    if not aliases:
        return None

    alias = aliases[0]
    if alias in ('text', 'none'):
        return None

    label = _normalize_language_label(alias)
    common_labels = {
        'PYTHON', 'JS', 'TS', 'SHELL', 'HTML', 'XML', 'CSS', 'SCSS',
        'JSON', 'YAML', 'MD', 'DIFF', 'SQL',
    }
    return label if label in common_labels else None


def _detect_code_block_metadata(pre, fenced_code_blocks: List[Dict[str, Optional[str]]]) -> Tuple[Optional[str], Optional[str]]:
    """优先对齐 Markdown 里记录的围栏信息与渲染后的 DOM，再在缺失时降级为自动猜测。

Prefer exact matches between fenced source snapshots and sanitized ``pre`` bodies, otherwise delegate to lexical guessing helpers.
"""
    code = pre.find('code')
    code_text = _normalize_code_text(code.get_text() if code else pre.get_text())

    for block in fenced_code_blocks:
        if not block['used'] and block['code'] == code_text:
            block['used'] = True
            if block['language']:
                return block['language'], block.get('title')
            break

    return _guess_language_label(code_text), None

# 辅助函数：标准化日期时间对象为纯日期 / Normalize datetime/date values to bare dates
def standardize_date(dt_obj: Any) -> date:
    """把 ``datetime`` 或 ``date`` 规整为不带时间的 ``date``，未知类型退回当天。

    Normalize ``datetime`` instances to calendar dates while passing ``date`` through unchanged; unrelated inputs gracefully fall back to ``date.today()`` in legacy behavior.
"""
    if isinstance(dt_obj, datetime):
        return dt_obj.date()
    elif isinstance(dt_obj, date):
        return dt_obj
    return date.today() 

# -------------------------------------------------------------------------
# 【TOC／目录 slugify】专门为 Markdown TOC 扩展输出设计
# Heading slugifier tailored for the Markdown TOC extension pipeline
# -------------------------------------------------------------------------
def my_custom_slugify(s: str, separator: str) -> str:
    """
    自定义 slugify，用于 TOC 生成的锚文本，兼顾中文与国际字符的稳定可读性。

    Custom slug formatter for generated table-of-contents anchors, balancing CJK readability with portable URL fragments.
"""
    s = str(s).lower().strip()
    
    # 1. Unicode NFKD：削弱重音字形 / Normalize diacritics via Unicode NFKD
    s = unicodedata.normalize('NFKD', s)
    
    # 2. 去除非 [\w\s-]，保留字母数字下划线与中文字符 / Strip glyphs outside alphanumeric, CJK, space, hyphen
    s = re.sub(r'[^\w\s-]', '', s)
    
    # 3. 收敛空白与连字符为分隔符并清理首尾 / Collapse whitespace and hyphen runs, trim separators
    s = re.sub(r'[\s-]+', separator, s).strip(separator)
    return s

# -------------------------------------------------------------------------
# 【标签／Tag slug】用于导出标签页的 URL 段
# Slug formatter dedicated to persisted tag URLs
# -------------------------------------------------------------------------
def tag_to_slug(tag_name: str) -> str:
    """
    针对中文场景的友好 slug：保留需要的字符，随后在路由层进行二次编码。

    CJK-aware slug derivation that trims unsafe punctuation yet keeps meaningful characters URL-encodable downstream.
"""
    # 1. 转为小写以统一比对 / Fold case for canonical comparisons
    slug = tag_name.lower()

    # 2. Unicode NFKD 解除组合音标 / Normalize international marks with NFKD decomposition
    slug = unicodedata.normalize('NFKD', slug)
    
    # 3. 仅保留允许的 token（Python 3 里 \w 含中文 Unicode 属性）/ Keep Unicode-aware \w glyphs plus spaces/hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    
    # 4. 将空白与 hyphen 规整为单一的 ``-`` 并裁切边界 / Compress whitespace-hyphen combos into single '-' delimiters
    slug = re.sub(r'[\s-]+', '-', slug).strip('-')
    return slug

def get_metadata_and_content(md_file_path: str) -> Tuple[Dict[str, Any], str, str, str]:
    """
    读取 Markdown 文件的 YAML Frontmatter，完成元数据推导、预处理与 Markdown→HTML（含 TOC）渲染。

    Loads front matter, derives defaults (dates, titles, excerpt), preprocesses shorthand syntax, renders HTML, and emits the TOC fragment alongside sanitized markup.
"""
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file {md_file_path}: {e}")
        return {}, "", "", ""

    # 拆分 Frontmatter 与正文 Markdown / Separate YAML preamble from prose
    match = re.match(r'---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

    if match:
        yaml_data = match.group(1)
        content_markdown = content[len(match.group(0)):]
        try:
            metadata = yaml.safe_load(yaml_data) or {}
        except yaml.YAMLError as exc:
            print(f"Error parsing YAML frontmatter in {md_file_path}: {exc}")
            metadata = {}
    else:
        metadata = {}
        content_markdown = content

    
    # --- 元数据处理 / Metadata enrichment ---
    
    # 1. date 字段格式化 / Normalize published dates
    raw_date = metadata.get('date')
    if raw_date:
        metadata['date'] = standardize_date(raw_date)
        metadata['date_formatted'] = metadata['date'].strftime('%Y-%m-%d')
    else:
        metadata['date'] = date.today()
        metadata['date_formatted'] = metadata['date'].strftime('%Y-%m-%d')
        
    # 2. tags（支持字符串或序列） / Coerce comma-separated strings into slugged records
    tags_list = metadata.get('tags', [])
    if isinstance(tags_list, str):
        tags_list = [t.strip() for t in tags_list.split(',')]
    
    metadata['tags'] = [
        {'name': t, 'slug': tag_to_slug(t)} 
        for t in tags_list if t
    ]

    # 3. slug：缺省时自文件名推导 / Fallback slug inference from filenames
    if 'slug' not in metadata:
        file_name = os.path.basename(md_file_path)
        base_name = os.path.splitext(file_name)[0]
        slug_match = re.match(r'^(\d{4}-\d{2}-\d{2}-)?(.*)$', base_name)
        if slug_match and slug_match.group(2):
            metadata['slug'] = slug_match.group(2).lower()
        else:
            metadata['slug'] = base_name.lower()
    
    # 4. title：缺省时自 slug／首段推算 / Fallback title from slug or first line
    if 'title' not in metadata:
        metadata['title'] = metadata['slug'].replace('-', ' ').title()
        if not metadata['title'] and content_markdown:
             metadata['title'] = content_markdown.split('\n', 1)[0].strip()
    
    # 5. summary／excerpt 汇总成模板所需的 excerpt / Map summary/description to excerpt slots
    metadata['excerpt'] = metadata.get('summary') or metadata.get('excerpt') or metadata.get('description') or ''

    content_markdown = _convert_colon_admonitions(content_markdown)
    content_markdown = _convert_emoticon_shorthands(content_markdown)
    
    # --- Markdown 渲染 / Markdown rendering ---
    
    # 1. 准备扩展配置拷贝 / Snapshot extension configs for mutation safety
    extension_configs = config.MARKDOWN_EXTENSION_CONFIGS.copy()
    
    # 动态注入 TOC 所需的 slugify 回调 / Inject custom TOC slugifier hook when enabled
    if 'toc' in extension_configs:
        extension_configs['toc']['slugify'] = my_custom_slugify
    
    md = markdown.Markdown(
        extensions=config.MARKDOWN_EXTENSIONS, 
        extension_configs=extension_configs, 
        output_format='html5',
    )
    
    fenced_code_blocks = _extract_fenced_code_blocks(content_markdown)
    content_markdown = _normalize_fenced_code_attributes(content_markdown)

    # 2. Markdown → HTML（核心转换） / Core Markdown to HTML conversion
    content_html = md.convert(content_markdown)
    
    # -------------------------------------------------------------------------
    # 【重构】UI：懒加载图像、语义化脚注与代码块封装等
    # Post-render DOM surgery for lazy assets, captions, wrappers, semantics
    # -------------------------------------------------------------------------
    # 使用 BeautifulSoup 做可控的 AST 改写 / Trusted HTML rewriting via BeautifulSoup
    if '<img' in content_html or '<table' in content_html or '<pre' in content_html or 'arithmatex' in content_html or 'footnote' in content_html or 'task-list' in content_html:
        soup = BeautifulSoup(content_html, 'html.parser')
        i18n = _get_i18n()

        _render_mathml(soup)
        _add_footnote_semantics(soup, i18n)
        _add_task_list_semantics(soup, i18n)

        # 1. 图片懒加载占位与解码提示 / Lazy-load tuning & async decoding hints
        for img in soup.find_all('img'):
            # ``loading`` 未显式写出时默认为 lazy / Default missing lazy hints explicitly
            if not img.get('loading'):
                img['loading'] = 'lazy'
            if not img.get('decoding'):
                img['decoding'] = 'async'
            if not img.get('width') or not img.get('height'):
                local_image_path = _resolve_local_image_path(img.get('src', ''), md_file_path)
                if local_image_path:
                    dimensions = _read_image_dimensions(local_image_path)
                    if dimensions:
                        width, height = dimensions
                        img.setdefault('width', str(width))
                        img.setdefault('height', str(height))

        # 2. 表格语义与横向滚动封装 / Semantic wrappers for wide tables & captions
        for table in soup.find_all('table'):
            caption_text = _extract_table_caption(table)
            if caption_text and not table.find('caption'):
                table.insert(0, _build_table_caption(soup, caption_text, i18n))

            # Markdown 对齐 style → class，减少 CSP unsafe-inline / Map alignment styles into classes for CSP
            for cell in table.find_all(['th', 'td']):
                style = cell.get('style', '')
                if 'text-align' in style:
                    if 'center' in style:
                        cell['class'] = cell.get('class', []) + ['align-center']
                    elif 'right' in style:
                        cell['class'] = cell.get('class', []) + ['align-right']
                    elif 'left' in style:
                        cell['class'] = cell.get('class', []) + ['align-left']
                    del cell['style']

            # 定位外层父节点以供包裹 / Locate immediate parent wrapper candidate
            parent = table.parent
            if not parent:
                continue

            # 避免重复套用 ``table-wrapper`` / Skip if already nested inside wrapper
            if 'class' in parent.attrs and 'table-wrapper' in parent['class']:
                continue

            caption = table.find('caption')
            caption_label = caption_text or (caption.get_text(" ", strip=True) if caption else "")
            wrapper_label = (
                i18n.get('table_scroll_region_label', 'Horizontally scrollable table: {caption}').format(caption=caption_label)
                if caption
                else i18n.get('table_scroll_region_fallback_label', 'Horizontally scrollable table')
            )
            wrapper_div = soup.new_tag(
                'div',
                attrs={
                    'class': 'table-wrapper',
                    'role': 'region',
                    'tabindex': '0',
                    'aria-label': wrapper_label,
                },
            )
            
            # ``table.replace_with(wrapper)``：先占位再回迁 / Swap table node with wrapper scaffold
            table.replace_with(wrapper_div)
            
            # 将 ``table`` 重新挂入 wrapper / Re-append the original table subtree under the wrapper
            wrapper_div.append(table)

        # 3. 代码语言徽章与 diff 行语义 / Code language chips & diff semantics
        for pre in soup.find_all('pre'):
            language_label, code_title = _detect_code_block_metadata(pre, fenced_code_blocks)
            pre['tabindex'] = '0'
            pre['aria-label'] = i18n.get('code_block_label', 'Code block')
            if not language_label and not code_title:
                continue

            parent = pre.parent
            if code_title:
                pre['data-title'] = code_title
                if parent and 'highlight' in parent.get('class', []):
                    parent['data-title'] = code_title

            if not language_label:
                continue

            pre['data-lang'] = language_label
            pre['aria-label'] = i18n.get('code_block_language_label', 'Code block, language {language}').format(language=language_label)
            if language_label == 'DIFF':
                _add_diff_line_semantics(soup, pre, i18n)
            if parent and 'highlight' in parent.get('class', []):
                parent['data-lang'] = language_label
            code = pre.find('code')
            if code:
                code_classes = code.get('class', [])
                language_class = f"language-{language_label.lower()}"
                if language_class not in code_classes:
                    code['class'] = code_classes + [language_class]
            
        content_html = str(soup)
    
    # 3. TOC 片段 / Consume rendered TOC markup if available
    toc_html = md.toc if hasattr(md, 'toc') else ""

    return metadata, content_markdown, content_html, toc_html
