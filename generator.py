# generator.py / HTML 页面与 Feed 生成器

import os
import shutil 
import glob   
from datetime import datetime, timezone
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional 
from jinja2 import Environment, FileSystemLoader
import json 
import re 
import html
import config
from i18n import get_translations
from parser import tag_to_slug 
from bs4 import BeautifulSoup 

# --- Jinja2 环境配置 / Jinja2 environment setup ---
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=True,
    trim_blocks=True, 
    lstrip_blocks=True
)

RAW_HTML_BLOCK_RE = re.compile(
    r'(<(?:pre|textarea|script|style)\b[^>]*>.*?</(?:pre|textarea|script|style)>)',
    re.IGNORECASE | re.DOTALL,
)


def minify_html_content(html_content: str) -> str:
    """压缩生成的 HTML，同时保留代码块等原始空白敏感区域。
    Minify generated HTML while preserving whitespace-sensitive blocks."""
    if not getattr(config, 'HTML_MINIFY', True):
        return html_content

    raw_blocks = []

    def preserve_raw_block(match: re.Match) -> str:
        raw_blocks.append(match.group(0))
        return f"___HTML_MINIFY_RAW_BLOCK_{len(raw_blocks) - 1}___"

    minified = RAW_HTML_BLOCK_RE.sub(preserve_raw_block, html_content)
    minified = re.sub(r'<!--(?!\[if).*?-->', '', minified, flags=re.DOTALL)
    minified = re.sub(r'>\s+<', '><', minified)
    minified = re.sub(r'^[ \t]+', '', minified, flags=re.MULTILINE).strip()

    for index, raw_block in enumerate(raw_blocks):
        minified = minified.replace(f"___HTML_MINIFY_RAW_BLOCK_{index}___", raw_block)

    return minified


def write_html_file(output_path: str, html_content: str) -> None:
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(minify_html_content(html_content))


def get_i18n() -> Dict[str, Any]:
    return get_translations(getattr(config, 'SITE_LANGUAGE', 'zh-CN'))


def get_common_template_context() -> Dict[str, Any]:
    """Site-wide template variables injected into every page render."""
    return {
        'index_page_title': getattr(config, 'INDEX_PAGE_TITLE', '') or config.BLOG_TITLE,
        'index_page_subtitle': getattr(config, 'INDEX_PAGE_SUBTITLE', ''),
        'github_repo_url': getattr(config, 'GITHUB_REPO_URL', '').strip(),
        'footer_content_type': config.FOOTER_CONTENT_TYPE,
        'footer_custom_text': config.FOOTER_CUSTOM_TEXT,
    }


def render_template(template, context: Dict[str, Any]) -> str:
    i18n = get_i18n()
    template_context = {
        'i18n': i18n,
        'site_language': i18n.get('html_lang', 'zh-cn'),
        **get_common_template_context(),
        **context,
    }
    return template.render(template_context)


def get_copyright_notice(title, author, url, license_config=None):
    """根据当前界面语言生成版权声明文本。
    Build the copyright notice for the active UI language."""
    if license_config is None:
        license_config = config.COPYRIGHT_LICENSE

    license_type = license_config.get('type', 'CC_BY_NC_4.0')
    if license_type == 'CUSTOM':
        return license_config.get('custom_text', '')

    i18n = get_i18n()
    notices = i18n.get('copyright_license_notices', {})
    text = notices.get(license_type) or notices.get('CC_BY_NC_4.0', '')

    if not text:
        # 兼容用户仍在 config.py 的 allowed_types 中手动覆盖 text 的情况。
        # Fallback when config.py still overrides license text manually in allowed_types.
        license_info = license_config.get('allowed_types', {}).get(license_type, {})
        text = license_info.get('text', '')

    return text.replace('{url}', url).replace('{title}', title).replace('{author}', author)


def get_copyright_format(title, author, url, license_config=None):
    """生成当前界面语言下的标准引用格式。
    Build the standard citation format for the active UI language."""
    if license_config is None:
        license_config = config.COPYRIGHT_LICENSE

    template_str = license_config.get('format_template') or get_i18n().get('copyright_format_template', '')
    return template_str.format(title=title, author=author, url=url)


def get_copyright_additional_note(license_config=None) -> str:
    if license_config is None:
        license_config = config.COPYRIGHT_LICENSE

    return license_config.get('additional_note') or get_i18n().get('copyright_additional_note', '')


# --- 辅助函数：路径和 URL / Path and URL helpers ---

def get_site_root_prefix() -> str:
    """获取网站在部署环境中的相对子目录路径前缀。
    Return the deployment subpath prefix used for internal links."""
    root = config.REPO_SUBPATH.strip()
    if not root or root == '/':
        config.SITE_ROOT = '' 
        return ''
    root = root.rstrip('/')
    config.SITE_ROOT = root if root.startswith('/') else f'/{root}'
    return config.SITE_ROOT

def make_internal_url(path: str) -> str:
    """生成规范化的内部 URL (Pretty URL: /slug/)。
    Build a normalized internal URL with pretty permalink style."""
    if not path:
        return ""
        
    normalized_path = path if path.startswith('/') else f'/{path}'
    site_root = get_site_root_prefix()
    
    # 移除 .html 后缀，除非是特殊文件 / Strip .html except special files
    if normalized_path.lower().endswith('.html') and \
       not normalized_path.lower().endswith(config.RSS_FILE) and \
       not normalized_path.lower().endswith(config.ATOM_FILE) and \
       not normalized_path.lower().endswith(config.SITEMAP_FILE) and \
       not normalized_path.lower() == '/404.html':
        normalized_path = normalized_path[:-5]
    
    if normalized_path.lower() == '/index': 
        normalized_path = '/'
    elif normalized_path.lower() == '/404' or normalized_path.lower() == '/404.html':
        # 404 页面通常不需要 url 后缀，或者保持原样 / Keep 404 path as-is
        pass 
    elif normalized_path.lower().endswith(config.RSS_FILE):
        pass
    elif normalized_path.lower().endswith(config.ATOM_FILE):
        pass
    elif normalized_path.lower().endswith(config.SITEMAP_FILE):
        pass
    elif normalized_path != '/' and not normalized_path.endswith('/'):
        normalized_path = f'{normalized_path}/'
    
    if not site_root:
        return normalized_path
    
    if normalized_path == '/':
        return f"{site_root}/"
    
    return f"{site_root}{normalized_path}"

def is_post_hidden(post: Dict[str, Any]) -> bool:
    """检查文章是否应被隐藏。
    Return True when a post should be hidden from public lists."""
    return post.get('status', 'published').lower() == 'draft' or post.get('hidden') is True

# --- 数据清洗函数 / Post data normalization ---

def process_posts_for_template(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """深度清洗文章列表链接。
    Normalize internal links inside post list data."""
    cleaned_posts = []
    for post in posts:
        new_post = post.copy()
        if 'link' in new_post:
            new_post['link'] = make_internal_url(new_post['link'])
        if 'prev_post_nav' in new_post and new_post['prev_post_nav']:
            nav = new_post['prev_post_nav'].copy()
            nav['link'] = make_internal_url(nav['link'])
            new_post['prev_post_nav'] = nav
        if 'next_post_nav' in new_post and new_post['next_post_nav']:
            nav = new_post['next_post_nav'].copy()
            nav['link'] = make_internal_url(nav['link'])
            new_post['next_post_nav'] = nav
        if 'tags' in new_post and new_post['tags']:
            cleaned_tags = []
            for tag in new_post['tags']:
                tag_copy = tag.copy()
                tag_path = f"{config.TAGS_DIR_NAME}/{tag_copy['slug']}"
                tag_copy['link'] = make_internal_url(tag_path) 
                cleaned_tags.append(tag_copy)
            new_post['tags'] = cleaned_tags
        cleaned_posts.append(new_post)
    return cleaned_posts

# --- 核心生成函数 / Core page generators ---

def _static_asset_exists(relative_name: str) -> bool:
    """检查源 static 目录下的资源文件是否真实存在。

    避免 JSON-LD 输出指向 404 的图片 URL（Google Rich Results 会因此降权）。

    Check whether a static asset exists before emitting structured-data image URLs.
    Avoid pointing rich-result metadata at missing images.
    """
    candidate = os.path.join(os.path.dirname(__file__), config.STATIC_DIR, relative_name)
    return os.path.isfile(candidate)


def _site_relative_asset_exists(url_path: str) -> bool:
    """检查站点根相对路径（如 /logo.png 或 /static/x.png）在构建产物中是否存在。

    JSON-LD 输出前用它过滤掉 Markdown 中纯演示性质的 404 图片引用，
    防止结构化数据校验失败或被搜索引擎降权。

    Check whether a site-root-relative asset exists in the build output before JSON-LD.
    Filters demo-only broken image URLs so structured data validation does not fail.
    """
    rel = url_path.lstrip('/')
    if not rel:
        return False
    project_root = os.path.dirname(__file__)
    candidates = [
        os.path.join(project_root, config.BUILD_DIR, rel),
        os.path.join(project_root, rel),
    ]
    return any(os.path.isfile(p) for p in candidates)


def get_json_ld_schema(post: Dict[str, Any]) -> str:
    """生成 Article 类型的 JSON-LD 结构化数据。

    image / publisher.logo 仅在对应静态资源存在时输出，缺失时整字段省略，
    防止结构化数据指向不存在的 URL。

    Build Article JSON-LD. Omit image and publisher.logo when assets are missing
    so structured data never points at broken URLs.
    """
    base_url = config.BASE_URL.rstrip('/')
    site_root = get_site_root_prefix()

    image_url: Optional[str] = None
    soup = BeautifulSoup(post['content_html'], 'html.parser')
    img_tag = soup.find('img')

    if img_tag and img_tag.get('src'):
        src = img_tag['src'].strip()
        if src.startswith(('http://', 'https://', '//')):
            image_url = src
        elif _site_relative_asset_exists(src):
            relative_path = src.lstrip('/')
            image_url = f"{base_url}{site_root}/{relative_path}"

    if image_url is None and _static_asset_exists('default-cover.png'):
        image_url = f"{base_url}{site_root}/static/default-cover.png"

    schema: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post['title'],
        "datePublished": post['date'].isoformat(),
        "dateModified": post['date'].isoformat(),
        "author": {
            "@type": "Person",
            "name": config.BLOG_AUTHOR
        },
        "publisher": {
            "@type": "Organization",
            "name": config.BLOG_TITLE,
        },
        "description": post.get('excerpt', config.BLOG_DESCRIPTION),
        "mainEntityOfPage": {
            "@type": "WebPage",
            "url": f"{base_url}{make_internal_url(post['link'])}"
        }
    }

    if image_url:
        schema["image"] = image_url

    if _static_asset_exists('logo.png'):
        schema["publisher"]["logo"] = {
            "@type": "ImageObject",
            "url": f"{base_url}{site_root}/static/logo.png"
        }

    return json.dumps(schema, ensure_ascii=False, indent=4)

def generate_index_html(sorted_posts: List[Dict[str, Any]], build_time_info: str):
    """生成首页
    Generate the homepage (index.html)."""
    try:
        i18n = get_i18n()
        output_path = os.path.join(config.BUILD_DIR, 'index.html')
        visible_posts = [p for p in sorted_posts if not is_post_hidden(p)][:config.MAX_POSTS_ON_INDEX]

        template = env.get_template('base.html')
        index_title = getattr(config, 'INDEX_PAGE_TITLE', '') or config.BLOG_TITLE
        context = {
            'page_id': 'index',
            'page_title': index_title,
            'blog_title': config.BLOG_TITLE,
            'blog_description': config.BLOG_DESCRIPTION,
            'blog_author': config.BLOG_AUTHOR,
            'posts': process_posts_for_template(visible_posts),
            'max_posts_on_index': config.MAX_POSTS_ON_INDEX,
            'site_root': get_site_root_prefix(),
            'current_year': datetime.now().year,
            'css_filename': config.CSS_FILENAME,
            'canonical_url': f"{config.BASE_URL.rstrip('/')}{get_site_root_prefix()}/",
            'footer_time_info': build_time_info,
            'footer_content_type': config.FOOTER_CONTENT_TYPE,
            'footer_custom_text': config.FOOTER_CUSTOM_TEXT,
        }
        
        html_content = render_template(template, context)
        write_html_file(output_path, html_content)
        print("Generated: index.html")
    except Exception as e:
        print(f"Error index.html: {e}")


def generate_archive_html(sorted_posts: List[Dict[str, Any]], build_time_info: str):
    """生成归档页 (archive/index.html)
    Generate the archive page."""
    try:
        i18n = get_i18n()
        output_dir = os.path.join(config.BUILD_DIR, 'archive')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'index.html')
        
        visible_posts = [p for p in sorted_posts if not is_post_hidden(p)]
        
        archive_by_year = defaultdict(list)
        for post in visible_posts:
            archive_by_year[post['date'].year].append(post)
        
        sorted_archive = sorted(archive_by_year.items(), key=lambda item: item[0], reverse=True)

        template = env.get_template('base.html')
        
        archive_html = "<div class=\"archive-page\">\n"

        if not sorted_archive:
            archive_html += f"<p class=\"empty-state\">{i18n['no_archive']}</p>\n"
        else:
            for year, posts in sorted_archive:
                archive_html += f"<h2 class=\"archive-year\">{year} <small>({len(posts)})</small></h2>\n"
                archive_html += "<ul class=\"archive-list\">\n"
            
                for post in posts:
                    link = make_internal_url(post['link']) 
                    date_str = post['date'].strftime('%m-%d')
                
                    archive_html += f"""
                    <li class="archive-item">
                        <span class="archive-date">{date_str}</span>
                        <a class="archive-link" href="{link}">{post['title']}</a>
                    </li>
                    """
                archive_html += "</ul>\n"
            
        archive_html += "</div>"
            
        context = {
            'page_id': 'archive',
            'page_title': i18n['page_archive'],
            'blog_title': config.BLOG_TITLE,
            'blog_description': i18n['page_archive'],
            'blog_author': config.BLOG_AUTHOR,
            'content_html': archive_html, 
            'posts': [],
            'site_root': get_site_root_prefix(),
            'current_year': datetime.now().year,
            'css_filename': config.CSS_FILENAME,
            'canonical_url': f"{config.BASE_URL.rstrip('/')}{make_internal_url('/archive')}",
            'footer_time_info': build_time_info,
            'footer_content_type': config.FOOTER_CONTENT_TYPE,
            'footer_custom_text': config.FOOTER_CUSTOM_TEXT,
        }
        
        html_content = render_template(template, context)
        write_html_file(output_path, html_content)
        print("Generated: archive/index.html")
    except Exception as e:
        print(f"Error archive.html: {e}")


def generate_tags_list_html(tag_map: Dict[str, List[Dict[str, Any]]], build_time_info: str):
    """生成标签列表页
    Generate the tag cloud listing page."""
    try:
        i18n = get_i18n()
        output_dir = os.path.join(config.BUILD_DIR, 'tags')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'index.html')
        
        sorted_tags = sorted(tag_map.items(), key=lambda item: len(item[1]), reverse=True)
        tags_html = f"<h1>{i18n['tags_list_heading']}</h1>\n<div class=\"tag-cloud\">\n"

        if not sorted_tags:
            tags_html += f"<p class=\"empty-state\">{i18n['no_tags']}</p>\n"
        else:
            for tag, posts in sorted_tags:
                tag_slug = tag_to_slug(tag)
                link = make_internal_url(f"{config.TAGS_DIR_NAME}/{tag_slug}")
                count = len(posts)
                tags_html += f"<a href=\"{link}\" class=\"tag-cloud-item\">{tag} ({count})</a>\n"
        tags_html += "</div>\n"

        template = env.get_template('base.html')
        context = {
            'page_id': 'tags',
            'page_title': i18n['page_tags'],
            'blog_title': config.BLOG_TITLE,
            'blog_description': i18n['page_tags'],
            'blog_author': config.BLOG_AUTHOR,
            'content_html': tags_html,
            'site_root': get_site_root_prefix(),
            'current_year': datetime.now().year,
            'css_filename': config.CSS_FILENAME,
            'canonical_url': f"{config.BASE_URL.rstrip('/')}{make_internal_url('/tags')}",
            'footer_time_info': build_time_info,
            'footer_content_type': config.FOOTER_CONTENT_TYPE,
            'footer_custom_text': config.FOOTER_CUSTOM_TEXT,
        }
        
        html_content = render_template(template, context)
        write_html_file(output_path, html_content)
        print("Generated: tags/index.html")
    except Exception as e:
        print(f"Error tags.html: {e}")


def generate_feed_html(sorted_posts: List[Dict[str, Any]], build_time_info: str):
    """生成 RSS 订阅说明页 (feed/index.html)
    Generate the human-readable feed discovery page."""
    try:
        i18n = get_i18n()
        output_dir = os.path.join(config.BUILD_DIR, 'feed')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'index.html')

        base_url = config.BASE_URL.rstrip('/')
        rss_path = make_internal_url(config.RSS_FILE)
        atom_path = make_internal_url(config.ATOM_FILE)
        rss_url = f"{base_url}{rss_path}"
        atom_url = f"{base_url}{atom_path}"
        recent_posts = [p for p in sorted_posts if not is_post_hidden(p)][:5]

        feed_html = f"""
        <div class="feed-page">
            <h1>{i18n['page_feed']}</h1>
            <p class="feed-intro">{i18n['feed_intro']}</p>

            <div class="feed-card">
                <p class="feed-label">{i18n.get('feed_rss_url_label', i18n['feed_url_label'])}</p>
                <p><a href="{rss_path}" class="feed-url">{rss_url}</a></p>
                <p class="feed-label">{i18n.get('feed_atom_url_label', 'Atom URL')}</p>
                <p><a href="{atom_path}" class="feed-url">{atom_url}</a></p>
            </div>
        """

        if recent_posts:
            feed_html += f"<h2>{i18n['recent_posts']}</h2>\n<ul class=\"feed-preview-list\">\n"
            for post in recent_posts:
                link = make_internal_url(post['link'])
                title = html.escape(post['title'])
                date_str = post['date'].strftime('%Y-%m-%d')
                feed_html += f"""
                <li class="feed-preview-item">
                    <span class="feed-preview-date">{date_str}</span>
                    <a href="{link}">{title}</a>
                </li>
                """
            feed_html += "</ul>\n"
        else:
            feed_html += f"<p class=\"empty-state\">{i18n['no_posts']}</p>\n"

        feed_html += "</div>"

        template = env.get_template('base.html')
        context = {
            'page_id': 'feed',
            'page_title': i18n['page_feed'],
            'blog_title': config.BLOG_TITLE,
            'blog_description': i18n['feed_description'],
            'blog_author': config.BLOG_AUTHOR,
            'content_html': feed_html,
            'site_root': get_site_root_prefix(),
            'current_year': datetime.now().year,
            'css_filename': config.CSS_FILENAME,
            'canonical_url': f"{base_url}{make_internal_url('/feed')}",
            'footer_time_info': build_time_info,
            'footer_content_type': config.FOOTER_CONTENT_TYPE,
            'footer_custom_text': config.FOOTER_CUSTOM_TEXT,
        }

        html_content = render_template(template, context)
        write_html_file(output_path, html_content)
        print("Generated: feed/index.html")
    except Exception as e:
        print(f"Error feed.html: {e}")


def generate_tag_page(tag_name: str, sorted_tag_posts: List[Dict[str, Any]], build_time_info: str):
    """生成单个标签页面
    Generate a single tag detail page."""
    try:
        i18n = get_i18n()
        tag_slug = tag_to_slug(tag_name)
        output_dir = os.path.join(config.BUILD_DIR, config.TAGS_DIR_NAME, tag_slug)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'index.html')

        template = env.get_template('base.html')
        processed_posts = process_posts_for_template(sorted_tag_posts)
        
        context = {
            'page_id': 'tag',
            'page_title': f"{i18n['page_tag_prefix']}: {tag_name}",
            'blog_title': config.BLOG_TITLE,
            'blog_description': config.BLOG_DESCRIPTION,
            'blog_author': config.BLOG_AUTHOR,
            'posts': processed_posts, 
            'tag': tag_name, 
            'site_root': get_site_root_prefix(),
            'current_year': datetime.now().year,
            'css_filename': config.CSS_FILENAME,
            'canonical_url': f"{config.BASE_URL.rstrip('/')}{make_internal_url(f'{config.TAGS_DIR_NAME}/{tag_slug}')}",
            'footer_time_info': build_time_info,
            'footer_content_type': config.FOOTER_CONTENT_TYPE,
            'footer_custom_text': config.FOOTER_CUSTOM_TEXT,
        }
        
        html_content = render_template(template, context)
        write_html_file(output_path, html_content)
        print(f"Generated tag page: {tag_name}")
    except Exception as e:
        print(f"Error tag page {tag_name}: {e}")

def generate_robots_txt():
    """生成 robots.txt
    Generate robots.txt."""
    try:
        output_path = os.path.join(config.BUILD_DIR, 'robots.txt')
        content = f"User-agent: *\nAllow: /\nSitemap: {config.BASE_URL.rstrip('/')}{make_internal_url(config.SITEMAP_FILE)}\n"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Generated: robots.txt")
    except Exception as e:
        print(f"Error robots.txt: {e}")

def generate_sitemap(parsed_posts: List[Dict[str, Any]]) -> str:
    """生成 sitemap.xml
    Generate sitemap.xml content."""
    urls = []
    base_url = config.BASE_URL.rstrip('/')
    
    for path, prio in [('/', '1.0'), ('/archive', '0.8'), ('/tags', '0.8'), ('/feed', '0.6'), ('/404', '0.1'), (config.RSS_FILE, '0.1'), (config.ATOM_FILE, '0.1')]:
        urls.append(f"<url><loc>{base_url}{make_internal_url(path)}</loc><priority>{prio}</priority></url>")

    if os.path.exists(os.path.join(config.BUILD_DIR, 'about', 'index.html')):
         urls.append(f"<url><loc>{base_url}{make_internal_url('/about')}</loc><priority>0.8</priority></url>")

    all_tags = set()
    for post in parsed_posts:
        if is_post_hidden(post) or not post.get('link'): continue
        link = f"{base_url}{make_internal_url(post['link'])}"
        lastmod = post['date'].strftime('%Y-%m-%d')
        urls.append(f"<url><loc>{link}</loc><lastmod>{lastmod}</lastmod><priority>0.6</priority></url>")
        for tag in post.get('tags', []):
            all_tags.add(tag['name'])
    
    for tag in all_tags:
        slug = tag_to_slug(tag)
        link = f"{base_url}{make_internal_url(f'{config.TAGS_DIR_NAME}/{slug}')}"
        urls.append(f"<url><loc>{link}</loc><priority>0.5</priority></url>")

    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{"".join(urls)}</urlset>'

def _feed_datetime(post: Dict[str, Any]) -> datetime:
    return datetime.combine(post['date'], datetime.min.time(), tzinfo=timezone.utc)


def _feed_updated_at(visible_posts: List[Dict[str, Any]]) -> datetime:
    dated_posts = [post for post in visible_posts if post.get('date')]
    if not dated_posts:
        return datetime.now(timezone.utc)
    return max(_feed_datetime(post) for post in dated_posts)


def _feed_posts(parsed_posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [post for post in parsed_posts if not is_post_hidden(post) and post.get('link')]


def generate_rss(parsed_posts: List[Dict[str, Any]]) -> str:
    """生成 RSS Feed
    Generate RSS 2.0 feed XML."""
    items = []
    base_url = config.BASE_URL.rstrip('/')
    visible_posts = _feed_posts(parsed_posts)
    
    for post in visible_posts[:10]:
        link = f"{base_url}{make_internal_url(post['link'])}"
        pub_date = _feed_datetime(post).strftime('%a, %d %b %Y %H:%M:%S +0000')
        categories = "".join(f"<category>{html.escape(tag['name'])}</category>" for tag in post.get('tags', []))
        summary = html.escape(post.get('excerpt') or config.BLOG_DESCRIPTION)
        items.append(
            f"<item>"
            f"<title>{html.escape(post['title'])}</title>"
            f"<link>{link}</link>"
            f"<pubDate>{pub_date}</pubDate>"
            f"<guid isPermaLink=\"true\">{link}</guid>"
            f"<dc:creator>{html.escape(config.BLOG_AUTHOR)}</dc:creator>"
            f"{categories}"
            f"<description>{summary}</description>"
            f"<content:encoded><![CDATA[{post['content_html']}]]></content:encoded>"
            f"</item>"
        )
    
    rss_link = make_internal_url(config.RSS_FILE) 
    atom_link = make_internal_url(config.ATOM_FILE)
    language = get_i18n().get('html_lang', 'zh-cn')
    updated_at = _feed_updated_at(visible_posts).strftime('%a, %d %b %Y %H:%M:%S +0000')
    return f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>{html.escape(config.BLOG_TITLE)}</title><link>{base_url}{make_internal_url("/")}</link><description>{html.escape(config.BLOG_DESCRIPTION)}</description><language>{language}</language><atom:link href="{base_url}{rss_link}" rel="self" type="application/rss+xml" /><atom:link href="{base_url}{atom_link}" rel="alternate" type="application/atom+xml" /><lastBuildDate>{updated_at}</lastBuildDate>{"".join(items)}</channel></rss>'


def generate_atom(parsed_posts: List[Dict[str, Any]]) -> str:
    """生成 Atom Feed。
    Generate Atom feed XML."""
    entries = []
    base_url = config.BASE_URL.rstrip('/')
    site_url = f"{base_url}{make_internal_url('/')}"
    atom_url = f"{base_url}{make_internal_url(config.ATOM_FILE)}"
    rss_url = f"{base_url}{make_internal_url(config.RSS_FILE)}"
    visible_posts = _feed_posts(parsed_posts)
    updated_at = _feed_updated_at(visible_posts).isoformat().replace('+00:00', 'Z')

    for post in visible_posts[:10]:
        link = f"{base_url}{make_internal_url(post['link'])}"
        published = _feed_datetime(post).isoformat().replace('+00:00', 'Z')
        categories = "".join(f"<category term=\"{html.escape(tag['name'])}\" />" for tag in post.get('tags', []))
        summary = html.escape(post.get('excerpt') or config.BLOG_DESCRIPTION)
        entries.append(
            f"<entry>"
            f"<title>{html.escape(post['title'])}</title>"
            f"<link href=\"{link}\" />"
            f"<id>{link}</id>"
            f"<published>{published}</published>"
            f"<updated>{published}</updated>"
            f"<author><name>{html.escape(config.BLOG_AUTHOR)}</name></author>"
            f"{categories}"
            f"<summary>{summary}</summary>"
            f"<content type=\"html\">{html.escape(post['content_html'])}</content>"
            f"</entry>"
        )

    return f'<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom" xml:lang="{get_i18n().get("html_lang", "zh-cn")}"><title>{html.escape(config.BLOG_TITLE)}</title><subtitle>{html.escape(config.BLOG_DESCRIPTION)}</subtitle><link href="{site_url}" rel="alternate" type="text/html" /><link href="{atom_url}" rel="self" type="application/atom+xml" /><link href="{rss_url}" rel="alternate" type="application/rss+xml" /><id>{site_url}</id><updated>{updated_at}</updated><author><name>{html.escape(config.BLOG_AUTHOR)}</name></author>{"".join(entries)}</feed>'

def generate_page_html(content_html: str, page_title: str, page_id: str, canonical_path_with_html: str, build_time_info: str):
    """生成通用页面（404 输出在站点根目录）
    Generate generic pages (404 is written to site root as 404.html)."""
    try:
        if page_id == '404':
            # 404 生成在根目录 404.html / 404 at _site/404.html
            output_dir = config.BUILD_DIR
            output_path = os.path.join(output_dir, '404.html')
        else:
            # 其他页面使用 /slug/index.html / Other pages use /slug/index.html
            output_dir = os.path.join(config.BUILD_DIR, page_id)
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, 'index.html')
        
        template = env.get_template('base.html')
        canonical_path = make_internal_url(canonical_path_with_html) 
        
        context = {
            'page_id': page_id,
            'page_title': page_title,
            'blog_title': config.BLOG_TITLE,
            'blog_description': config.BLOG_DESCRIPTION,
            'blog_author': config.BLOG_AUTHOR,
            'content_html': content_html, 
            'site_root': get_site_root_prefix(),
            'current_year': datetime.now().year,
            'css_filename': config.CSS_FILENAME,
            'canonical_url': f"{config.BASE_URL.rstrip('/')}{canonical_path}",
            'footer_time_info': build_time_info,
            'footer_content_type': config.FOOTER_CONTENT_TYPE,
            'footer_custom_text': config.FOOTER_CUSTOM_TEXT,
            'json_ld_schema': None, 
        }
        
        html_content = render_template(template, context)
        write_html_file(output_path, html_content)
        print(f"Generated: {output_path} (Page ID: {page_id})")

    except Exception as e:
        print(f"Error {page_id}: {e}")

def generate_post_page(post: Dict[str, Any]):
    """生成单篇文章页面
    Generate a single post detail page."""
    try:
        relative_link = post.get('link')
        if not relative_link: return
        # 404 页面不通过此函数生成 / 404 is generated elsewhere
        if relative_link.lower() == '404.html': return

        clean_name = relative_link[:-5] if relative_link.lower().endswith('.html') else relative_link
        clean_name = clean_name.strip('/')
        output_dir = os.path.join(config.BUILD_DIR, clean_name)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'index.html')

        template = env.get_template('base.html')
        processed_list = process_posts_for_template([post])
        current_post_processed = processed_list[0]

        context = {
            'page_id': 'post',
            'page_title': post['title'],
            'blog_title': config.BLOG_TITLE,
            'blog_description': post.get('excerpt', config.BLOG_DESCRIPTION),
            'blog_author': config.BLOG_AUTHOR,
            'content_html': post['content_html'],
            'post': current_post_processed,
            'post_date': post.get('date_formatted', ''),
            'post_date_iso': post['date'].isoformat() if post.get('date') else '',
            'post_tags': current_post_processed.get('tags', []),
            'toc_html': post.get('toc_html'),
            'prev_post_nav': current_post_processed.get('prev_post_nav'),
            'next_post_nav': current_post_processed.get('next_post_nav'),
            'site_root': get_site_root_prefix(),
            'current_year': datetime.now().year,
            'css_filename': config.CSS_FILENAME,
            'canonical_url': f"{config.BASE_URL.rstrip('/')}{make_internal_url(relative_link)}",
            'footer_time_info': post.get('footer_time_info', ''),
            'footer_content_type': config.FOOTER_CONTENT_TYPE,
            'footer_custom_text': config.FOOTER_CUSTOM_TEXT,
            # 版权相关 / Copyright helpers
            'copyright_notice': get_copyright_notice,
            'copyright_format': get_copyright_format,
            'copyright_additional_note': get_copyright_additional_note(config.COPYRIGHT_LICENSE),
            'copyright_config': config.COPYRIGHT_LICENSE,
        }

        html_content = render_template(template, context)
        write_html_file(output_path, html_content)
        print(f"Generated: {output_path}")

    except Exception as e:
        print(f"Error generating post {post.get('title')}: {e}")