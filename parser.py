# parser.py

import os
import re
import yaml
import json
import markdown
from datetime import datetime, date
from typing import Dict, Any, Tuple, Optional, List
import config 
import unicodedata 
from bs4 import BeautifulSoup, NavigableString # 引入 BeautifulSoup
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
    """用标准库读取常见图片尺寸，避免为懒加载图片引入布局偏移。"""
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
    """将 Markdown 图片 src 解析为本地文件路径；外链不处理。"""
    if not src or src.startswith(('http://', 'https://', '//', 'data:')):
        return None

    project_root = os.path.dirname(__file__)
    if src.startswith('/'):
        candidate = os.path.join(project_root, src.lstrip('/'))
    else:
        candidate = os.path.join(os.path.dirname(md_file_path), src)

    return candidate if os.path.isfile(candidate) else None


def _convert_colon_admonitions(markdown_text: str) -> str:
    """兼容 VuePress/VitePress 风格 ::: tip 提示块。"""
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
    """将常见 ASCII 表情简写转换为 emoji，同时避开代码围栏和行内代码。"""
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
    """支持 ```python title="file.py" 这类更直观的代码块属性写法。"""
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
    """统一代码文本格式，便于 Markdown 原文和渲染后 HTML 做匹配。"""
    return code.replace('\r\n', '\n').replace('\r', '\n').strip('\n')


def _render_mathml(soup: BeautifulSoup) -> None:
    """将 arithmatex 生成的 TeX 包装节点替换为静态 MathML。"""
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
    """将语言别名转换成短标签，用于代码块右上角显示。"""
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
    """从围栏代码块的 info string 中提取语言名。"""
    first_token = info.strip().split(maxsplit=1)[0] if info.strip() else ''
    if not first_token:
        return None

    # 支持 Python-Markdown attr_list 风格：``` {.python}
    attr_match = re.search(r'\.([A-Za-z0-9_+#-]+)', first_token)
    if attr_match:
        first_token = attr_match.group(1)

    label = _normalize_language_label(first_token)
    return label or None


def _title_from_fence_info(info: str) -> Optional[str]:
    """从围栏代码块的 info string 中提取可选标题。"""
    match = re.search(r'''(?:^|\s)title=(?:"([^"]*)"|'([^']*)'|([^\s]+))''', info)
    if not match:
        return None

    title = next((group for group in match.groups() if group is not None), '').strip()
    return title or None


def _extract_fenced_code_blocks(markdown_text: str) -> List[Dict[str, Optional[str]]]:
    """提取围栏代码块，用声明语言补充渲染后的 HTML。"""
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
    """未声明语言时，使用 Pygments 做最佳努力的语言猜测。"""
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
    """优先使用围栏声明的代码块信息，无法匹配时再尝试自动猜测语言。"""
    code = pre.find('code')
    code_text = _normalize_code_text(code.get_text() if code else pre.get_text())

    for block in fenced_code_blocks:
        if not block['used'] and block['code'] == code_text:
            block['used'] = True
            if block['language']:
                return block['language'], block.get('title')
            break

    return _guess_language_label(code_text), None

# 辅助函数 - 将日期时间对象标准化为日期对象
def standardize_date(dt_obj: Any) -> date:
    """将 datetime 或 date 对象标准化为 date 对象。"""
    if isinstance(dt_obj, datetime):
        return dt_obj.date()
    elif isinstance(dt_obj, date):
        return dt_obj
    return date.today() 

# -------------------------------------------------------------------------
# 【TOC/目录专用 Slugify】: 专为 Markdown TOC 扩展设计
# -------------------------------------------------------------------------
def my_custom_slugify(s: str, separator: str) -> str:
    """
    自定义 slugify 函数，用于 Markdown TOC 锚点生成。
    兼容中文和国际字符。
    """
    s = str(s).lower().strip()
    
    # 1. Unicode 规范化 (NFKD) 处理重音等字符
    s = unicodedata.normalize('NFKD', s)
    
    # 2. 移除所有非 \w (字母、数字、下划线, 包含中文), 非空格, 非横线的字符
    s = re.sub(r'[^\w\s-]', '', s)
    
    # 3. 将空格和多个横线替换为单个横线，并移除首尾横线
    s = re.sub(r'[\s-]+', separator, s).strip(separator)
    return s

# -------------------------------------------------------------------------
# 【标签/Tag 专用 Slugify】: 用于生成标签页面的 URL
# -------------------------------------------------------------------------
def tag_to_slug(tag_name: str) -> str:
    """
    [中文兼容性优化] 将标签名转换为 URL 友好的 slug。
    此版本兼容中文、英文及其他国际字符，并保留中文字符（最终会 URL 编码）。
    """
    # 1. 小写
    slug = tag_name.lower()

    # 2. Unicode 规范化 (NFKD): 处理重音符号等国际字符。
    slug = unicodedata.normalize('NFKD', slug)
    
    # 3. 移除所有非 \w (字母、数字、下划线, 包含中文), 非空格, 非横线的字符。
    #    Python 3 的 \w 默认是 Unicode-aware 的，会正确保留中文字符。
    slug = re.sub(r'[^\w\s-]', '', slug)
    
    # 4. 将空格和多个横线替换为单个横线，并移除首尾横线
    slug = re.sub(r'[\s-]+', '-', slug).strip('-')
    return slug

def get_metadata_and_content(md_file_path: str) -> Tuple[Dict[str, Any], str, str, str]:
    """
    从 Markdown 文件中读取 Frontmatter 元数据和内容。
    返回: (metadata, content_markdown, content_html, toc_html)
    """
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file {md_file_path}: {e}")
        return {}, "", "", ""

    # 分隔 Frontmatter 和内容
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

    
    # --- 元数据处理 ---
    
    # 1. date
    raw_date = metadata.get('date')
    if raw_date:
        metadata['date'] = standardize_date(raw_date)
        metadata['date_formatted'] = metadata['date'].strftime('%Y-%m-%d')
    else:
        metadata['date'] = date.today()
        metadata['date_formatted'] = metadata['date'].strftime('%Y-%m-%d')
        
    # 2. tags
    tags_list = metadata.get('tags', [])
    if isinstance(tags_list, str):
        tags_list = [t.strip() for t in tags_list.split(',')]
    
    metadata['tags'] = [
        {'name': t, 'slug': tag_to_slug(t)} 
        for t in tags_list if t
    ]

    # 3. slug
    if 'slug' not in metadata:
        file_name = os.path.basename(md_file_path)
        base_name = os.path.splitext(file_name)[0]
        slug_match = re.match(r'^(\d{4}-\d{2}-\d{2}-)?(.*)$', base_name)
        if slug_match and slug_match.group(2):
            metadata['slug'] = slug_match.group(2).lower()
        else:
            metadata['slug'] = base_name.lower()
    
    # 4. title
    if 'title' not in metadata:
        metadata['title'] = metadata['slug'].replace('-', ' ').title()
        if not metadata['title'] and content_markdown:
             metadata['title'] = content_markdown.split('\n', 1)[0].strip()
    
    # 5. summary/excerpt (保留摘要功能)
    metadata['excerpt'] = metadata.get('summary') or metadata.get('excerpt') or metadata.get('description') or ''

    content_markdown = _convert_colon_admonitions(content_markdown)
    content_markdown = _convert_emoticon_shorthands(content_markdown)
    
    # --- Markdown 渲染 ---
    
    # 1. 准备配置
    extension_configs = config.MARKDOWN_EXTENSION_CONFIGS.copy()
    
    # 动态注入 slugify 函数
    if 'toc' in extension_configs:
        extension_configs['toc']['slugify'] = my_custom_slugify
    
    md = markdown.Markdown(
        extensions=config.MARKDOWN_EXTENSIONS, 
        extension_configs=extension_configs, 
        output_format='html5',
    )
    
    fenced_code_blocks = _extract_fenced_code_blocks(content_markdown)
    content_markdown = _normalize_fenced_code_attributes(content_markdown)

    # 2. 转换
    content_html = md.convert(content_markdown)
    
    # -------------------------------------------------------------------------
    # [重构] UI 增强：图片懒加载 (Lazy Load) 和表格包裹器
    # -------------------------------------------------------------------------
    # 使用 BeautifulSoup 来进行安全、可靠的 HTML 变换
    if '<img' in content_html or '<table' in content_html or '<pre' in content_html or 'arithmatex' in content_html or 'footnote' in content_html or 'task-list' in content_html:
        soup = BeautifulSoup(content_html, 'html.parser')
        i18n = _get_i18n()

        _render_mathml(soup)
        _add_footnote_semantics(soup, i18n)
        _add_task_list_semantics(soup, i18n)

        # 1. 图片懒加载 (Lazy Load)
        for img in soup.find_all('img'):
            # 只有当图片没有明确的 'loading' 属性时才添加 'lazy'
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

        # 2. 表格包裹器 (Table Wrapper)
        for table in soup.find_all('table'):
            caption_text = _extract_table_caption(table)
            if caption_text and not table.find('caption'):
                table.insert(0, _build_table_caption(soup, caption_text, i18n))

            # 将 Markdown 表格对齐生成的 inline style 转成 class，便于 CSP 去掉 unsafe-inline。
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

            # 找到 table 标签的父元素
            parent = table.parent
            if not parent:
                continue

            # 检查父元素是否已经是 table-wrapper，防止重复包裹
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
            
            # 将 table 替换为 wrapper_div
            table.replace_with(wrapper_div)
            
            # 将 table 放入 wrapper_div
            wrapper_div.append(table)

        # 3. 代码块语言标签
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
    
    # 3. 获取目录
    toc_html = md.toc if hasattr(md, 'toc') else ""

    return metadata, content_markdown, content_html, toc_html
