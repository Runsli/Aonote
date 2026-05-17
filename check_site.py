import posixpath
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import config


ERROR_PREFIX = "ERROR"
WARNING_PREFIX = "WARN"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags: List[Tuple[str, Dict[str, str]]] = []
        self.ids: Set[str] = set()
        self.title_parts: List[str] = []
        self.in_title = False
        self.has_h1 = False

    def handle_starttag(self, tag: str, attrs):
        attr_map = {name.lower(): (value or "") for name, value in attrs}
        tag = tag.lower()
        self.tags.append((tag, attr_map))

        element_id = attr_map.get("id")
        if element_id:
            self.ids.add(element_id)

        if tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.has_h1 = True

    def handle_endtag(self, tag: str):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str):
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return "".join(self.title_parts).strip()


def _site_path_for_html(build_dir: Path, html_path: Path) -> str:
    rel = html_path.relative_to(build_dir).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return f"/{rel[:-10]}"
    return f"/{rel}"


def _is_external_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https", "mailto", "tel", "data"}


def _resolve_internal_url(value: str, current_url_path: str) -> Tuple[Optional[str], Optional[str]]:
    if not value or _is_external_url(value):
        return None, None
    if value.startswith("javascript:"):
        return value, None

    parsed = urlparse(value)
    path = parsed.path
    fragment = parsed.fragment or None

    if not path:
        return current_url_path, fragment

    if path.startswith("/"):
        normalized_path = posixpath.normpath(path)
    else:
        base = current_url_path if current_url_path.endswith("/") else posixpath.dirname(current_url_path)
        normalized_path = posixpath.normpath(posixpath.join(base, path))

    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"
    if value.endswith("/") and not normalized_path.endswith("/"):
        normalized_path = f"{normalized_path}/"
    return normalized_path, fragment


def _path_exists_for_url(build_dir: Path, url_path: str) -> bool:
    rel = url_path.lstrip("/")
    if not rel:
        return (build_dir / "index.html").is_file()

    candidate = build_dir / rel
    if candidate.is_file():
        return True
    if candidate.is_dir() and (candidate / "index.html").is_file():
        return True
    if not Path(rel).suffix and (candidate / "index.html").is_file():
        return True
    return False


def _check_html_page(build_dir: Path, html_path: Path) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    html = html_path.read_text(encoding="utf-8", errors="replace")
    parser = PageParser()
    parser.feed(html)

    page_label = html_path.relative_to(build_dir).as_posix()
    current_url_path = _site_path_for_html(build_dir, html_path)
    is_404 = page_label == "404.html"

    if any(tag == "script" for tag, _ in parser.tags):
        errors.append(f"{page_label}: contains <script> tag")

    if not parser.title:
        errors.append(f"{page_label}: missing non-empty <title>")

    descriptions = [
        attrs.get("content", "").strip()
        for tag, attrs in parser.tags
        if tag == "meta" and attrs.get("name", "").lower() == "description"
    ]
    if not any(descriptions):
        errors.append(f"{page_label}: missing non-empty meta description")

    canonicals = [
        attrs.get("href", "").strip()
        for tag, attrs in parser.tags
        if tag == "link" and attrs.get("rel", "").lower() == "canonical"
    ]
    if is_404:
        if canonicals:
            errors.append(f"{page_label}: 404 page should not declare canonical")
        has_noindex = any(
            tag == "meta"
            and attrs.get("name", "").lower() == "robots"
            and "noindex" in attrs.get("content", "").lower()
            for tag, attrs in parser.tags
        )
        if not has_noindex:
            errors.append(f"{page_label}: 404 page should include robots noindex")
    elif not canonicals:
        errors.append(f"{page_label}: missing canonical link")

    if not parser.has_h1:
        warnings.append(f"{page_label}: missing <h1>")

    for tag, attrs in parser.tags:
        if tag == "a":
            href = attrs.get("href", "").strip()
            url_path, fragment = _resolve_internal_url(href, current_url_path)
            if url_path == href and href.startswith("javascript:"):
                errors.append(f"{page_label}: javascript: link is not allowed")
                continue
            if url_path is None:
                continue
            if not _path_exists_for_url(build_dir, url_path):
                errors.append(f"{page_label}: broken internal link {href!r}")
            elif fragment and url_path == current_url_path and fragment not in parser.ids:
                errors.append(f"{page_label}: broken same-page anchor {href!r}")
        elif tag in {"img", "source"}:
            src = attrs.get("src", "").strip()
            if not src or _is_external_url(src):
                continue
            url_path, _ = _resolve_internal_url(src, current_url_path)
            if url_path and not _path_exists_for_url(build_dir, url_path):
                errors.append(f"{page_label}: missing image/source asset {src!r}")
        elif tag == "link":
            href = attrs.get("href", "").strip()
            rel = attrs.get("rel", "").lower()
            if "canonical" in rel or not href or _is_external_url(href):
                continue
            url_path, _ = _resolve_internal_url(href, current_url_path)
            if url_path and not _path_exists_for_url(build_dir, url_path):
                errors.append(f"{page_label}: missing linked asset {href!r}")

    return errors, warnings


def run_checks(build_dir: str = config.BUILD_DIR) -> bool:
    root = Path(build_dir)
    errors: List[str] = []
    warnings: List[str] = []

    if not root.is_dir():
        print(f"{ERROR_PREFIX}: build directory not found: {root}")
        return False

    html_files = sorted(root.rglob("*.html"))
    if not html_files:
        print(f"{ERROR_PREFIX}: no HTML files found in {root}")
        return False

    for html_path in html_files:
        page_errors, page_warnings = _check_html_page(root, html_path)
        errors.extend(page_errors)
        warnings.extend(page_warnings)

    for required_file in (config.SITEMAP_FILE, config.RSS_FILE, "robots.txt"):
        if not (root / required_file).is_file():
            errors.append(f"missing required file: {required_file}")

    for warning in warnings:
        print(f"{WARNING_PREFIX}: {warning}")
    for error in errors:
        print(f"{ERROR_PREFIX}: {error}")

    if errors:
        print(f"Site health check failed: {len(errors)} error(s), {len(warnings)} warning(s).")
        return False

    print(f"Site health check passed: {len(html_files)} HTML page(s), {len(warnings)} warning(s).")
    return True


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else config.BUILD_DIR
    raise SystemExit(0 if run_checks(target_dir) else 1)
