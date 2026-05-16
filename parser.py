# parser.py

import os
import re
import yaml
import markdown
from datetime import datetime, date
from typing import Dict, Any, Tuple, Optional
import config 
import unicodedata 
from bs4 import BeautifulSoup # 引入 BeautifulSoup


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
    
    # 2. 转换
    content_html = md.convert(content_markdown)
    
    # -------------------------------------------------------------------------
    # [重构] UI 增强：图片懒加载 (Lazy Load) 和表格包裹器
    # -------------------------------------------------------------------------
    # 使用 BeautifulSoup 来进行安全、可靠的 HTML 变换
    if '<img' in content_html or '<table' in content_html:
        soup = BeautifulSoup(content_html, 'html.parser')

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
            # 找到 table 标签的父元素
            parent = table.parent
            if not parent:
                continue

            # 检查父元素是否已经是 table-wrapper，防止重复包裹
            if 'class' in parent.attrs and 'table-wrapper' in parent['class']:
                continue

            # 创建新的 div 容器
            wrapper_div = soup.new_tag('div', attrs={'class': 'table-wrapper'})
            
            # 将 table 替换为 wrapper_div
            table.replace_with(wrapper_div)
            
            # 将 table 放入 wrapper_div
            wrapper_div.append(table)
            
        content_html = str(soup)
    
    # 3. 获取目录
    toc_html = md.toc if hasattr(md, 'toc') else ""

    return metadata, content_markdown, content_html, toc_html
