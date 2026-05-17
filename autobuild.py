# autobuild.py — 静态站点增量构建编排 / Incremental static site build orchestrator

import os
import shutil
import glob
import hashlib
import json
from typing import List, Dict, Any, Set, Optional 
from collections import defaultdict
from datetime import datetime, timezone, timedelta 
import subprocess 
import shlex      

import config
from parser import get_metadata_and_content
import generator
import check_site

# 尝试导入csscompressor，如果未安装则使用基础压缩 / Try importing csscompressor; use basic compression if not installed
try:
    import csscompressor
    CSS_COMPRESSOR_AVAILABLE = True
except ImportError:
    CSS_COMPRESSOR_AVAILABLE = False
    print("Warning: csscompressor not installed, using basic compression")

# =========================================================================
# 组合输出目录变量定义在模块顶层，避免 config 属性缺失 / Combined output dir vars at module level
# =========================================================================
# 这些变量现在是 autobuild.py 模块的全局变量，确保可用 / These are module-level globals in autobuild.py for reliable access
POSTS_OUTPUT_DIR = os.path.join(config.BUILD_DIR, config.POSTS_DIR_NAME)
TAGS_OUTPUT_DIR = os.path.join(config.BUILD_DIR, config.TAGS_DIR_NAME)
STATIC_OUTPUT_DIR = os.path.join(config.BUILD_DIR, config.STATIC_DIR)
# =========================================================================


# 增量构建清单文件路径 / Manifest file path for incremental builds
MANIFEST_FILE = os.path.join(os.path.dirname(__file__), '.build_manifest.json')

# 定义 UTC+8 时区信息 / UTC+8 timezone info
TIMEZONE_OFFSET = timedelta(hours=8)
TIMEZONE_INFO = timezone(TIMEZONE_OFFSET)

# --- Manifest 辅助函数 / Manifest helper functions (incremental build) ---
def load_manifest() -> Dict[str, Any]:
    """加载上一次的构建清单文件。

    Load persisted incremental metadata or yield an empty manifest when unreadable.
    """
    try:
        with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_manifest(manifest: Dict[str, Any]):
    """保存当前的构建清单文件。

    Persist structured manifest snapshots for incremental rebuild skips.
    """
    try:
        with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"警告：无法写入构建清单文件 {MANIFEST_FILE}: {e}")

def get_full_content_hash(filepath: str) -> str:
    """计算文件的完整 SHA256 哈希值。用于 Manifest。

    Compute deterministic SHA256 for entire-file contents powering manifest diffs.
    """
    h = hashlib.sha256()
    try:
        # 使用路径相对路径进行存储，但在计算哈希时使用绝对路径 / Store relative paths; hash using absolute paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(script_dir, filepath)

        with open(full_path, 'rb') as file:
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                h.update(chunk)
    except IOError:
        return ""
    return h.hexdigest()

# 计算文件哈希 / Compute file content hash
def get_file_hash(filepath: str) -> Optional[str]:
    """计算文件的 SHA256 哈希值。

    Produce a full-file SHA hex digest unless the backing path suddenly disappears.
    """
    try:
        # 获取脚本所在目录的绝对路径，用于构建文件的完整路径 / Script dir absolute path for full file path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(script_dir, filepath)

        if not os.path.exists(full_path):
            return None
            
        sha256 = hashlib.sha256()
        with open(full_path, 'rb') as f:
            # 分块读取文件以处理大文件 / Read file in chunks for large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256.update(byte_block)
        return sha256.hexdigest()
    except Exception:
        return None


# 检查依赖 & Hash 文件 (保持不变) / Check dependencies & hash files (unchanged)
try:
    # 尝试导入 Pygments 以确保代码高亮功能可用 / Try importing Pygments for syntax highlighting
    import pygments
except ImportError:
    pass

def hash_file(filepath: str) -> str:
    """计算文件的 SHA256 哈希值前 8 位。用于 CSS 文件名。

    Return first eight hexadecimal chars of SHA256 fingerprints for hashed asset names.
    """
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()[:8]
    except FileNotFoundError:
        return 'nohash'


def post_sort_key(post: Dict[str, Any]):
    """文章排序键：日期优先，同一天内按 slug 稳定排序。

    Tuple key prefers publication timestamps and falls back to a normalized slug for stability.
    """
    stable_slug = str(post.get('slug') or post.get('link') or '').lower()
    return post['date'], stable_slug

# 获取文件最后修改时间 (Git -> 文件系统 -> 回退) / Get file mtime (Git -> filesystem -> fallback)
def format_file_mod_time(filepath: str) -> str:
    """
    获取文件的最后修改时间。
    优先级：1. Git Author Time -> 2. 文件系统修改时间 -> 3. 当前构建时间。
    并确保输出包含微秒以保证唯一性。

    Derive deterministic footer timestamps with Git author dates first, then filesystem mtimes,
    finally the current UTC clock, always projecting into UTC+8 with microsecond precision.
    """

    def format_dt(dt: datetime, source: str) -> str:
        # 确保 datetime 对象带有正确的时区信息 / Ensure datetime has correct timezone info
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            # 将 Naive datetime 视为 UTC，再转换到 UTC+8 / Treat naive datetimes as UTC, convert to UTC+8
            dt = dt.replace(tzinfo=timezone.utc).astimezone(TIMEZONE_INFO) 
        else:
            # 否则直接转换为 UTC+8 / Otherwise convert directly to UTC+8
            dt = dt.astimezone(TIMEZONE_INFO)
            
        # 使用微秒 (%f) 格式化时间 / Format time with microseconds (%f)
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S.%f')
        
        # 移除末尾的零和点，使输出更简洁，但保留非零微秒 / Strip trailing zeros/dots; keep non-zero microseconds
        time_str = time_str.rstrip('0').rstrip('.')
        
        return f"本文构建时间: {time_str} (UTC+8 - {source})"
    
    # --- 1. 尝试获取 Git 最后提交时间 / Try Git last commit time (author time) ---
    try:
        git_command = ['git', 'log', '-1', '--pretty=format:%aI', '--', filepath]
        result = subprocess.run(git_command, capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            git_time_str = result.stdout.strip()
            if git_time_str:
                try:
                    mtime_dt_tz = datetime.fromisoformat(git_time_str)
                except ValueError:
                    if git_time_str.endswith('Z'):
                        git_time_str = git_time_str.replace('Z', '+00:00')
                    mtime_dt_tz = datetime.fromisoformat(git_time_str)
                
                return format_dt(mtime_dt_tz, 'Git')

    except Exception as e:
        pass 
    
    # --- 2. 尝试获取文件系统修改时间 / Try filesystem modification time (secondary fallback) ---
    try:
        timestamp = os.path.getmtime(filepath)
        # 将时间戳转换为 UTC timezone-aware 对象 / Convert timestamp to UTC-aware datetime
        fs_mtime = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return format_dt(fs_mtime, 'Filesystem')
        
    except FileNotFoundError:
        pass

    except Exception as e:
        pass
        
    # --- 3. 最终回退：使用当前构建时间 / Final fallback: current build time ---
    now_utc = datetime.now(timezone.utc)
    return format_dt(now_utc, 'Fallback')


def compress_css_content(css_content):
    """
    基础CSS压缩函数，去除注释和多余空白

    Lightweight regexp-based shrinker stripping block comments plus redundant whitespace.
    """
    import re
    # 移除CSS注释 / Remove CSS comments
    css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
    
    # 移除多余的空白字符和换行符 / Remove extra whitespace and newlines
    css_content = re.sub(r'\s+', ' ', css_content)
    
    # 移除选择器和属性之间的多余空格 / Remove extra spaces around selectors and properties
    css_content = re.sub(r'\s*([{}:;,>+~])\s*', r'\1', css_content)
    
    # 移除URL周围的空格 / Remove spaces around URLs
    css_content = re.sub(r'url\s*\(\s*', 'url(', css_content)
    css_content = re.sub(r'\s*\)', ')', css_content)
    
    # 移除十六进制颜色值中的多余零 / Shrink hex colors by dropping redundant digits
    css_content = re.sub(r'#([a-fA-F0-9])\1([a-fA-F0-9])\2([a-fA-F0-9])\3', r'#\1\2\3', css_content)
    
    # 移除小数点前的零 / Remove leading zero before decimal point
    css_content = re.sub(r'(?<=[\s:])0+\.([0-9]+)', r'.\1', css_content)
    
    # 移除分号前的空格 / Remove space before semicolon in closing brace
    css_content = re.sub(r';}', '}', css_content)
    
    # 去除首尾空格 / Strip leading and trailing whitespace
    css_content = css_content.strip()
    
    return css_content

def compress_css_file(input_path, output_path):
    """
    压缩CSS文件

    Emit a minified asset using csscompressor when available, otherwise the basic helper.
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        if CSS_COMPRESSOR_AVAILABLE:
            compressed_css = csscompressor.compress(css_content)
        else:
            # 使用基础压缩作为回退 / Use basic compression as fallback
            compressed_css = compress_css_content(css_content)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(compressed_css)
        
        # 计算压缩率 / Compute compression ratio
        original_size = len(css_content.encode('utf-8'))
        compressed_size = len(compressed_css.encode('utf-8'))
        compression_rate = (original_size - compressed_size) / original_size * 100
        
        print(f"   -> CSS compressed: {original_size / 1024:.2f}KB -> {compressed_size / 1024:.2f}KB ({compression_rate:.1f}% reduction)")
        
        return True
    except Exception as e:
        print(f"   -> CSS compression failed: {e}")
        return False

# 检查文章是否应被隐藏 / Check whether a post should be hidden
def is_post_hidden(post: Dict[str, Any]) -> bool:
    """检查文章是否应被隐藏。

    Posts marked draft/hidden disappear from chronological navigation injections.
    """
    return post.get('status', 'published').lower() == 'draft' or post.get('hidden') is True

def build_site():
    print("\n" + "="*40)
    print("   🚀 STARTING BUILD PROCESS (Incremental Build Enabled)")
    print("="*40 + "\n")
    
    # -------------------------------------------------------------------------
    # [1/5] 准备工作 & 增量构建初始化 (启用增量构建) / Prepare dirs and hydrate incremental manifests
    # -------------------------------------------------------------------------
    print("[1/5] Preparing build directory and loading manifest...")
    
    # 确保目录存在，不 rmtree 清理以保留上次构建产物 / Create dirs without wiping prior build output
    os.makedirs(config.BUILD_DIR, exist_ok=True) 
    # 引用模块顶层定义的输出目录变量 / Reference module-level output dir vars
    os.makedirs(POSTS_OUTPUT_DIR, exist_ok=True) 
    os.makedirs(TAGS_OUTPUT_DIR, exist_ok=True)
    os.makedirs(STATIC_OUTPUT_DIR, exist_ok=True)
    
    # 加载上次的构建清单 / Load previous build manifest
    old_manifest = load_manifest()
    new_manifest = {
        'posts': {}, 
        'static_files': {},
        'templates': {} # 模板和核心依赖项都存储在这里 / Templates and core dependencies stored here
    }
    
    # 存储需要重新生成 HTML 的文章对象 / Posts that need HTML regeneration
    posts_to_build: List[Dict[str, Any]] = [] 
    # 标志位：文章集合信息是否变化 (影响列表页、RSS、Sitemap) / Flag: post set changed (affects list pages, RSS, sitemap)
    posts_data_changed = False      
    # 主题或模板文件是否变化 / Whether theme or template files changed
    theme_changed = False

    # -------------------------------------------------------------------------
    # [2/5] 资源处理 & 主题/模板变动检查 / Assets sync plus theme/template drift detection
    # -------------------------------------------------------------------------
    print("\n[2/5] Processing Assets and Checking Theme Changes...")
    assets_dir = os.path.join(config.BUILD_DIR, 'assets')
    os.makedirs(assets_dir, exist_ok=True)
    
    # 复制静态文件 (使用顶部定义的 STATIC_OUTPUT_DIR) / Copy static files (using STATIC_OUTPUT_DIR above)
    if os.path.exists(config.STATIC_DIR):
        shutil.copytree(config.STATIC_DIR, STATIC_OUTPUT_DIR, dirs_exist_ok=True)

    # -----------------------------------------------------------
    # 检查 CSS 变动并设置 theme_changed / Detect CSS changes and set theme_changed
    # -----------------------------------------------------------
    css_source = 'assets/style.css'
    if os.path.exists(css_source):
        css_hash = hash_file(css_source)
        new_css = f"style.{css_hash}.css"
        config.CSS_FILENAME = new_css
        
        # 使用压缩版本 / Use compressed version
        compressed_css_path = os.path.join(assets_dir, new_css)
        success = compress_css_file(css_source, compressed_css_path)
        
        if not success:
            # 如果压缩失败，回退到普通复制 / If compression fails, fall back to plain copy
            shutil.copy2(css_source, compressed_css_path)

        # 清理旧的 hash CSS，避免增量构建长期积累无用资源。 / Remove stale hashed CSS to avoid incremental build clutter
        for css_file in glob.glob(os.path.join(assets_dir, 'style.*.css')):
            if os.path.basename(css_file) != new_css:
                try:
                    os.remove(css_file)
                    print(f"   -> Removed stale CSS asset: {os.path.basename(css_file)}")
                except OSError as e:
                    print(f"   -> WARNING: Failed to remove stale CSS asset {css_file}: {e}")

        # 检查CSS文件内容是否变动 (使用 get_full_content_hash) / Check CSS content change (via get_full_content_hash)
        current_css_content_hash = get_full_content_hash(css_source)
        old_css_content_hash = old_manifest.get('static_files', {}).get(css_source)

        if current_css_content_hash != old_css_content_hash:
            theme_changed = True
            print(f"   -> [CHANGE DETECTED] {css_source} content has changed. (Theme Change)")
        
        new_manifest.setdefault('static_files', {})[css_source] = current_css_content_hash
    else:
        config.CSS_FILENAME = 'style.css'

    # -----------------------------------------------------------
    # 检查 base.html 变动并设置 theme_changed / Detect base.html changes and set theme_changed
    # -----------------------------------------------------------
    base_template_source = os.path.join('templates', 'base.html')
    if os.path.exists(base_template_source):
        current_template_hash = get_full_content_hash(base_template_source)
        old_template_hash = old_manifest.get('templates', {}).get(base_template_source)

        if current_template_hash != old_template_hash:
            theme_changed = True
            print(f"   -> [CHANGE DETECTED] {base_template_source} has changed. (Theme Change)")
        
        new_manifest.setdefault('templates', {})[base_template_source] = current_template_hash
    # -----------------------------------------------------------
    
    # =========================================================================
    # 检查核心 Python 与模板文件变动 / Check core Python and template file changes
    # 这一部分是解决问题的关键，确保构建逻辑更改时强制重建 / Key to forcing full rebuild when build logic changes
    # =========================================================================
    CORE_DEPENDENCIES = [
        'autobuild.py', 
        'parser.py', 
        'generator.py', 
        'config.py',
        'i18n.py',
        'check_site.py',
        # 重要的模板文件 / Important template files
        os.path.join('templates', 'post.html'),
        os.path.join('templates', 'list.html'),
        os.path.join('templates', 'archive.html'),
        os.path.join('templates', 'tags_list.html'),
    ]

    for core_file in CORE_DEPENDENCIES:
        if os.path.exists(core_file):
            current_core_hash = get_full_content_hash(core_file)
            # 使用 'templates' 键来存储所有非文章/非静态资源的依赖项哈希 / Store non-post/non-static dependency hashes under 'templates'
            old_core_hash = old_manifest.get('templates', {}).get(core_file)
            
            if current_core_hash != old_core_hash:
                theme_changed = True
                print(f"   -> [CHANGE DETECTED] Core dependency {core_file} has changed. (Theme/Logic Change)")
                
            new_manifest.setdefault('templates', {})[core_file] = current_core_hash
            
    # =========================================================================

    # =========================================================================
    # 复制 CNAME 到 _site 部署目录 / Copy CNAME into _site for custom domain
    # =========================================================================
    cname_path_source = os.path.join(os.path.dirname(__file__), 'CNAME')
    cname_path_dest = os.path.join(config.BUILD_DIR, 'CNAME')

    if os.path.exists(cname_path_source):
        print("   -> Copying CNAME file...")
        shutil.copyfile(cname_path_source, cname_path_dest)
    else:
        print("   -> WARNING: CNAME file not found. Custom domain might fail (404).")
    # =========================================================================

    # -------------------------------------------------------------------------
    # [3/5] 解析 Markdown (增量构建核心) / Parse Markdown with incremental skip rules
    # -------------------------------------------------------------------------
    print("\n[3/5] Parsing Markdown Files...")
    
    md_files = glob.glob(os.path.join(config.MARKDOWN_DIR, '*.md'))
    if not md_files: md_files = glob.glob('*.md')
    
    parsed_posts = []
    tag_map = defaultdict(list)
    source_md_paths: Set[str] = set()

    for md_file in md_files:
        relative_path = os.path.relpath(md_file, os.path.dirname(__file__)).replace('\\', '/')
        source_md_paths.add(relative_path)
        
        # [增量逻辑] 检查内容哈希 / [Incremental] Check content hash
        current_hash = get_full_content_hash(md_file)
        old_item = old_manifest.get('posts', {}).get(relative_path, {})
        old_hash = old_item.get('hash')

        needs_full_build = (current_hash != old_hash) or ('link' not in old_item)
        needs_rebuild_html = needs_full_build or theme_changed # 使用 theme_changed 控制 HTML 重建 / Use theme_changed to control HTML rebuild

        if needs_full_build:
            # 只有内容变更时才打印此信息 / Print this only when content actually changed
            if current_hash != old_hash:
                 print(f"   -> [CONTENT CHANGED] {os.path.basename(md_file)}")
            # 否则，如果是新增文件或缺失链接信息，下面会单独打印 / Else new file or missing link info is logged below
        elif theme_changed: # 只有主题变动时，才打印这条，否则上面的 needs_full_build 已经打印 / Log theme-only rebuild unless needs_full_build already logged
            print(f"   -> [REBUILD HTML] {os.path.basename(md_file)} (Theme changed)")
        else:
            print(f"   -> [SKIPPED HTML] {os.path.basename(md_file)}")
            
        # 解析内容 (即使跳过 HTML，也要解析元数据来构建列表页) / Parse content (metadata needed for list pages even if HTML skipped)
        metadata, content_md, content_html, toc_html = get_metadata_and_content(md_file)
        
        mod_time_cn = format_file_mod_time(md_file)  # 文件修改时间 / File modification time

        # 自动补全 slug 和特殊页面处理 (保持不变) / Auto-fill slug and special pages (unchanged)
        if 'slug' not in metadata:
            filename_slug = os.path.splitext(os.path.basename(md_file))[0]
            metadata['slug'] = filename_slug

        slug = str(metadata['slug']).lower()
        file_name = os.path.basename(md_file)
        
        # --- 特殊页面处理 / Special pages (404 / about) ---
        if slug == '404' or file_name == '404.md':
            special_link = '404.html'
            special_post = { 
                **metadata, 'content_html': content_html, 'toc_html': '', 
                'link': special_link, 'footer_time_info': mod_time_cn
            }
            # 404 使用 generate_page_html，而非 generate_post_page / 404 uses generate_page_html
            if needs_rebuild_html: # 使用 needs_rebuild_html / Use needs_rebuild_html
                generator.generate_page_html(
                    special_post['content_html'], 
                    special_post['title'], 
                    '404', 
                    special_link, 
                    special_post['footer_time_info']
                )

            new_manifest.setdefault('posts', {})[relative_path] = {'hash': current_hash, 'link': special_link}
            continue 

        if metadata.get('hidden') is True: 
            if slug == 'about' or file_name == config.ABOUT_PAGE:
                 special_link = 'about.html'
                 special_post = { 
                     **metadata, 'content_html': content_html, 'toc_html': '', 
                     'link': special_link, 'footer_time_info': mod_time_cn
                 }
                 # 特殊页面也需检查 theme_changed / Special pages respect theme_changed
                 if needs_rebuild_html: # 使用 needs_rebuild_html / Use needs_rebuild_html
                     generator.generate_page_html(
                         special_post['content_html'], special_post['title'], 
                         'about', special_link, special_post['footer_time_info']
                     )
            new_manifest.setdefault('posts', {})[relative_path] = {'hash': current_hash, 'link': 'hidden'}
            continue 

        if not all(k in metadata for k in ['date', 'title']): 
            continue
            
        # --- 普通文章处理 / Regular post handling ---
        # 链接格式：posts/slug.html (在 generator.py 中会被清洗为 /posts/slug/ 格式) / Link format posts/slug.html (generator normalizes to /posts/slug/)
        post_link = os.path.join(config.POSTS_DIR_NAME, f"{slug}.html").replace('\\', '/')
        post = {
            **metadata, 
            'content_markdown': content_md,
            'content_html': content_html,
            'toc_html': toc_html,
            'link': post_link,
            'footer_time_info': mod_time_cn 
        }
        
        # 1. 准备 NEW metadata for comparison (critical fields for list pages) / Prepare new manifest metadata for list-page comparison
        new_manifest_data = {
            'hash': current_hash,
            'title': post.get('title', ''),
            'date_str': post['date'].strftime('%Y-%m-%d') if post.get('date') else '',
            'link': post_link, 
            # 存储排好序的标签名称列表，以便准确对比 / Store sorted tag names for accurate comparison
            'tags_list': sorted([t['name'] for t in post.get('tags', [])]),
            'hidden': post.get('hidden', False),
            'status': post.get('status', 'published'),
        }

        # 2. 检查元数据是否变化 (忽略 hash 字段) / Check metadata changes (ignore hash field)
        metadata_changed = False
        for key, new_value in new_manifest_data.items():
            if key == 'hash': 
                continue
            
            # 使用 str() 确保布尔值、列表等数据类型能被准确对比 / Use str() so bools, lists, etc. compare reliably
            if str(new_value) != str(old_item.get(key)):
                metadata_changed = True
                break
                
        # 只要内容或元数据变化，列表页就需要重建 / Rebuild list pages when content or metadata changes
        needs_rebuild_list = needs_full_build or metadata_changed

        if metadata_changed and not needs_full_build:
            print(f"   -> [METADATA CHANGED] {os.path.basename(md_file)}")

        if needs_rebuild_list:
            posts_data_changed = True
        
        # 清理旧的 HTML 文件 (如果 Slug 变化) / Remove old HTML output if slug changed
        if old_item.get('link') and old_item.get('link') != post_link and old_item.get('link') != 'hidden' and old_item.get('link') != '404.html':
             # 确保路径是基于 BUILD_DIR 的，而不是相对于根目录 / Paths must be under BUILD_DIR, not repo root
             old_html_path_parts = old_item['link'].strip('/').split('/')
             old_html_dir = os.path.join(config.BUILD_DIR, *old_html_path_parts)
             
             try:
                 if os.path.exists(old_html_dir) and os.path.isdir(old_html_dir):
                     # 删除旧的 /slug/ 目录 / Delete old /slug/ directory
                     shutil.rmtree(old_html_dir) 
                     print(f"   -> [CLEANUP] Deleted old post directory: {old_html_dir}")
                 elif os.path.exists(old_html_dir):
                    # 处理 /post.html 模式（如果存在） / Handle legacy /post.html layout if present
                    os.remove(old_html_dir)
                    print(f"   -> [CLEANUP] Deleted old HTML file: {old_html_dir}")
             except Exception as e:
                 print(f"   -> [WARNING] Failed to clean up old post path {old_html_dir}: {e}")
                
        for tag_data in post.get('tags', []):
            tag_map[tag_data['name']].append(post)
            
        parsed_posts.append(post)

        # 3. 更新 Manifest (保存 Hash 和所有关键元数据) / Update manifest (hash and key metadata)
        new_manifest.setdefault('posts', {})[relative_path] = new_manifest_data
        
        # 只有当内容或链接/元数据发生变化，或者主题变动时，才需要重建文章详情页 / Rebuild post page when content, link/metadata, or theme changed
        if needs_rebuild_html:
            posts_to_build.append(post) 
            
    # 清理被删除的源文件 / Clean up removed source files
    deleted_paths = set(old_manifest.get('posts', {}).keys()) - source_md_paths
    for deleted_path in deleted_paths:
        item = old_manifest['posts'][deleted_path]
        deleted_link = item.get('link')
        print(f"   -> [DELETED] Source file {deleted_path} removed.")
        posts_data_changed = True 
        
        if deleted_link and deleted_link != 'hidden' and deleted_link != '404.html':
            # 确保路径是基于 BUILD_DIR 的 / Ensure path is under BUILD_DIR
            deleted_html_path_parts = deleted_link.strip('/').split('/')
            deleted_html_dir = os.path.join(config.BUILD_DIR, *deleted_html_path_parts)
            
            try:
                if os.path.exists(deleted_html_dir) and os.path.isdir(deleted_html_dir):
                    shutil.rmtree(deleted_html_dir)
                    print(f"   -> [CLEANUP] Deleted post directory: {deleted_html_dir}")
                else:
                    # 处理 /post.html 模式（如果存在） / Handle legacy /post.html layout if present
                    deleted_html_file = os.path.join(config.BUILD_DIR, deleted_link.strip('/'))
                    if os.path.exists(deleted_html_file):
                        os.remove(deleted_html_file)
                        print(f"   -> [CLEANUP] Deleted post HTML file: {deleted_html_file}")
            except Exception as e:
                 print(f"   -> [WARNING] Failed to clean up deleted path {deleted_html_dir}: {e}")
                 
            # 从新清单中移除已删除的文章记录 / Remove deleted post from new manifest
            new_manifest['posts'].pop(deleted_path, None)


    final_parsed_posts = sorted(parsed_posts, key=post_sort_key, reverse=True)
    
    print(f"   -> Successfully parsed {len(final_parsed_posts)} blog posts. ({len(posts_to_build)} HTML files rebuilt)")

    # -------------------------------------------------------------------------
    # [4/5] 上一篇/下一篇导航与站点构建时间 / Prev/next nav wiring and human-readable stamp
    # -------------------------------------------------------------------------
    
    # 仅对可见文章生成上/下导航 / Prev/next nav only for visible posts
    visible_posts_for_nav = [p for p in final_parsed_posts if not is_post_hidden(p)]
    
    for i, post in enumerate(visible_posts_for_nav):
        # 找到 post 在 final_parsed_posts 中的原始引用 (用于 posts_to_build 列表) / Original post ref in final_parsed_posts (for posts_to_build)
        original_post = next(p for p in final_parsed_posts if p['link'] == post['link'])

        prev_post_data = visible_posts_for_nav[i - 1] if i > 0 else None
        next_post_data = visible_posts_for_nav[i + 1] if i < len(visible_posts_for_nav) - 1 else None

        original_post['prev_post_nav'] = None
        if prev_post_data:
            original_post['prev_post_nav'] = {
                'title': prev_post_data['title'],
                'link': prev_post_data['link']
            }

        original_post['next_post_nav'] = None
        if next_post_data:
            original_post['next_post_nav'] = {
                'title': next_post_data['title'],
                'link': next_post_data['link']
            }

    now_utc = datetime.now(timezone.utc)
    now_utc8 = now_utc.astimezone(TIMEZONE_INFO)
    # 列表页使用不带微秒的简洁格式 / List pages use compact time without microseconds
    global_build_time_cn = f"网站构建时间: {now_utc8.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)"
    
    # -------------------------------------------------------------------------
    # [5/5] 生成 HTML (应用增量逻辑) / Emit HTML with incremental rebuild fan-out
    # -------------------------------------------------------------------------
    print("\n[5/5] Generating HTML...")
    
    # 1. 生成普通文章详情页 / Generate regular post detail pages
    # 文章数据变化时也重建全部文章页，确保上一篇/下一篇导航同步更新。 / Rebuild all post pages when post data changes so prev/next nav stays in sync
    posts_to_build_all = final_parsed_posts if (theme_changed or posts_data_changed) else posts_to_build
    
    if theme_changed and not posts_to_build:
        print("   -> [REBUILDING] ALL Post Pages (Theme changed, but no post content changed)")
    elif posts_data_changed:
        print("   -> [REBUILDING] ALL Post Pages (Post order or metadata changed)")

    # 如果主题/逻辑变动，posts_to_build_all 是所有文章，否则只是变动的文章 / theme_changed -> all posts; else only changed posts
    for post in posts_to_build_all:
        generator.generate_post_page(post) 

    # 2. 生成列表页 (应用增量逻辑) / Generate list pages (incremental logic)
    # posts_data_changed 或主题变动时重建列表页 / Rebuild list pages when data or theme changed
    if not old_manifest or posts_data_changed or theme_changed:
        print("   -> [REBUILDING] Index, Archive, Tags, RSS, Atom (Post data or Theme changed)")
        
        generator.generate_index_html(final_parsed_posts, global_build_time_cn) 
        generator.generate_archive_html(final_parsed_posts, global_build_time_cn) 
        generator.generate_tags_list_html(tag_map, global_build_time_cn) 
        generator.generate_feed_html(final_parsed_posts, global_build_time_cn)

        for tag, posts in tag_map.items():
            sorted_tag = sorted(posts, key=post_sort_key, reverse=True)
            generator.generate_tag_page(tag, sorted_tag, global_build_time_cn) 

        generator.generate_robots_txt()
        
        with open(os.path.join(config.BUILD_DIR, config.SITEMAP_FILE), 'w', encoding='utf-8') as f:
            f.write(generator.generate_sitemap(final_parsed_posts))
        with open(os.path.join(config.BUILD_DIR, config.RSS_FILE), 'w', encoding='utf-8') as f:
            f.write(generator.generate_rss(final_parsed_posts))
        with open(os.path.join(config.BUILD_DIR, config.ATOM_FILE), 'w', encoding='utf-8') as f:
            f.write(generator.generate_atom(final_parsed_posts))
            
    else:
        print("   -> [SKIPPED] Index, Archive, Tags, RSS, Atom (No post data or Theme change)")

    print("\n[post] Running site health checks...")
    if not check_site.run_checks(config.BUILD_DIR):
        raise SystemExit(1)

    # 3. 保存新的构建清单 / Save new build manifest
    # 健康检查通过后再保存 manifest / Save manifest only after health checks pass
    save_manifest(new_manifest)
    print("   -> Manifest file updated.")
    
    print("\n✅ BUILD COMPLETE")

if __name__ == '__main__':
    build_site()
