import posixpath
import xml.etree.ElementTree as ET
from argparse import ArgumentParser
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import DefaultDict, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import config
from bs4 import BeautifulSoup


ERROR_PREFIX = "ERROR"
WARNING_PREFIX = "WARN"
CHECK_CATEGORIES = ("A11Y", "SEO", "Links", "Assets", "Feeds", "No-JS", "Build")
GENERIC_LINK_TEXT = {
    "click here",
    "here",
    "read more",
    "more",
    "details",
    "点击这里",
    "这里",
    "更多",
    "详情",
}


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


def _line_for_element(html: str, element) -> int:
    marker = str(element)[:80]
    index = html.find(marker)
    if index == -1:
        return 0
    return html.count("\n", 0, index) + 1


def _visible_text(element) -> str:
    for hidden in element.select("[aria-hidden='true']"):
        hidden.extract()
    return " ".join(element.get_text(" ", strip=True).split())


def _is_complex_table(table) -> bool:
    rows = table.find_all("tr")
    first_row = rows[0] if rows else None
    column_count = len(first_row.find_all(["th", "td"])) if first_row else 0
    return column_count >= 4 or len(rows) >= 5


def _category_for_message(message: str) -> str:
    lower = message.lower()
    if any(term in lower for term in ("rss", "atom", "sitemap", "xml", "feed")):
        return "Feeds"
    if any(term in lower for term in ("link", "anchor", "href", "javascript:")):
        return "Links"
    if any(term in lower for term in ("image", "asset", "stylesheet", "source")):
        return "Assets"
    if any(term in lower for term in ("title", "description", "canonical", "robots", "noindex", "404")):
        return "SEO"
    if any(term in lower for term in ("script", "no-js")):
        return "No-JS"
    if any(term in lower for term in ("build directory", "html files", "required file")):
        return "Build"
    return "A11Y"


def _group_messages(messages: List[str]) -> DefaultDict[str, List[str]]:
    grouped: DefaultDict[str, List[str]] = defaultdict(list)
    for message in messages:
        grouped[_category_for_message(message)].append(message)
    return grouped


def _print_grouped_messages(prefix: str, messages: List[str]) -> None:
    grouped = _group_messages(messages)
    for category in CHECK_CATEGORIES:
        category_messages = grouped.get(category, [])
        if not category_messages:
            continue
        print(f"{prefix}: [{category}] {len(category_messages)} issue(s)")
        for message in category_messages:
            print(f"  - {message}")


def _print_category_summary(errors: List[str], warnings: List[str]) -> None:
    error_groups = _group_messages(errors)
    warning_groups = _group_messages(warnings)
    print("Health check categories:")
    for category in CHECK_CATEGORIES:
        error_count = len(error_groups.get(category, []))
        warning_count = len(warning_groups.get(category, []))
        status = "ok" if error_count == 0 and warning_count == 0 else f"{error_count} error(s), {warning_count} warning(s)"
        print(f"  - {category}: {status}")


def _check_accessibility(html: str, page_label: str) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    soup = BeautifulSoup(html, "html.parser")

    ids: Dict[str, int] = {}
    for element in soup.find_all(attrs={"id": True}):
        element_id = element.get("id", "").strip()
        if not element_id:
            continue
        ids[element_id] = ids.get(element_id, 0) + 1
    for element_id, count in ids.items():
        if count > 1:
            errors.append(f"{page_label}: duplicate id {element_id!r}")

    h1_count = len(soup.find_all("h1"))
    if h1_count == 0:
        warnings.append(f"{page_label}: missing <h1>")
    elif h1_count > 1:
        warnings.append(f"{page_label}: contains {h1_count} <h1> elements")

    previous_heading_level: Optional[int] = None
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        level = int(heading.name[1])
        if previous_heading_level and level > previous_heading_level + 1:
            line = _line_for_element(html, heading)
            suffix = f" near line {line}" if line else ""
            warnings.append(
                f"{page_label}: heading level jumps from h{previous_heading_level} to h{level}{suffix}"
            )
        previous_heading_level = level

    for img in soup.find_all("img"):
        alt = img.get("alt")
        src = img.get("src", "")
        if alt is None:
            errors.append(f"{page_label}: image missing alt text {src!r}")
        elif alt.strip().lower() in {"图片", "示例图片", "image", "photo", "picture"}:
            warnings.append(f"{page_label}: image alt text is too generic {src!r}")

    for pre in soup.find_all("pre"):
        if not pre.get("aria-label", "").strip():
            warnings.append(f"{page_label}: code block missing aria-label")
        if pre.get("tabindex") != "0":
            warnings.append(f"{page_label}: code block is not keyboard-scrollable")

    for diff_block in soup.select('.highlight[data-lang="DIFF"]'):
        for added_line in diff_block.select(".gi"):
            if not added_line.select_one(".diff-line-label"):
                warnings.append(f"{page_label}: diff added line missing screen-reader label")
        for removed_line in diff_block.select(".gd"):
            if not removed_line.select_one(".diff-line-label"):
                warnings.append(f"{page_label}: diff removed line missing screen-reader label")

    for table in soup.find_all("table"):
        if not table.find("caption") and _is_complex_table(table):
            warnings.append(f"{page_label}: complex table missing caption")
        wrapper = table.find_parent(class_="table-wrapper")
        if not wrapper:
            warnings.append(f"{page_label}: table missing scroll wrapper")
        else:
            if wrapper.get("tabindex") != "0":
                warnings.append(f"{page_label}: table wrapper is not keyboard-scrollable")
            if not wrapper.get("aria-label", "").strip():
                warnings.append(f"{page_label}: table wrapper missing aria-label")

    for footnote_ref in soup.select("a.footnote-ref"):
        if not footnote_ref.get("aria-label", "").strip():
            warnings.append(f"{page_label}: footnote reference missing aria-label")

    for footnote_backref in soup.select("a.footnote-backref"):
        if not footnote_backref.get("aria-label", "").strip():
            warnings.append(f"{page_label}: footnote back reference missing aria-label")
        title = footnote_backref.get("title", "").strip()
        if title and "Jump back" in title:
            warnings.append(f"{page_label}: footnote back reference title is not localized")

    for task_item in soup.select("li.task-list-item"):
        checkbox = task_item.find("input", attrs={"type": "checkbox"})
        if not checkbox:
            warnings.append(f"{page_label}: task list item missing checkbox")
            continue
        if not checkbox.get("aria-label", "").strip():
            warnings.append(f"{page_label}: task checkbox missing aria-label")
        if checkbox.get("aria-disabled") != "true":
            warnings.append(f"{page_label}: static task checkbox missing aria-disabled")
        if not task_item.select_one(".task-state-label"):
            warnings.append(f"{page_label}: task item missing screen-reader state label")

    for element in soup.find_all(attrs={"aria-label": True}):
        if not element.get("aria-label", "").strip():
            errors.append(f"{page_label}: empty aria-label on <{element.name}>")

    for link in soup.find_all("a"):
        href = link.get("href", "").strip()
        text = _visible_text(BeautifulSoup(str(link), "html.parser"))
        aria_label = link.get("aria-label", "").strip()
        title = link.get("title", "").strip()
        accessible_name = aria_label or text or title
        if not accessible_name and href and not href.startswith("#"):
            errors.append(f"{page_label}: link has no accessible text {href!r}")
        elif accessible_name.strip().lower() in GENERIC_LINK_TEXT:
            warnings.append(f"{page_label}: link text is too generic {href!r}")

    return errors, warnings


def _check_html_page(build_dir: Path, html_path: Path) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    html = html_path.read_text(encoding="utf-8", errors="replace")
    parser = PageParser()
    parser.feed(html)
    a11y_errors, a11y_warnings = _check_accessibility(html, html_path.relative_to(build_dir).as_posix())
    errors.extend(a11y_errors)
    warnings.extend(a11y_warnings)

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


def _check_xml_file(root: Path, filename: str, expected_root_suffix: str) -> List[str]:
    path = root / filename
    if not path.is_file():
        return [f"missing required file: {filename}"]

    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return [f"{filename}: invalid XML ({exc})"]

    root_tag = tree.getroot().tag
    if not root_tag.endswith(expected_root_suffix):
        return [f"{filename}: unexpected root element {root_tag!r}"]
    return []


def _is_focusable(element) -> bool:
    if element.has_attr("disabled"):
        return False
    tabindex = element.get("tabindex")
    if tabindex is not None:
        return tabindex.strip() != "-1"
    if element.name == "a":
        return element.has_attr("href")
    if element.name in {"button", "summary", "textarea", "select"}:
        return True
    if element.name == "input":
        return not element.has_attr("disabled") and element.get("type", "").lower() != "hidden"
    return False


def _element_accessible_name(element) -> str:
    aria_label = element.get("aria-label", "").strip()
    if aria_label:
        return aria_label
    title = element.get("title", "").strip()
    text = _visible_text(BeautifulSoup(str(element), "html.parser"))
    return text or title or "(no accessible name)"


def _focusable_description(element) -> str:
    classes = element.get("class", [])
    class_suffix = f".{'.'.join(classes)}" if classes else ""
    role = element.get("role", "")
    role_suffix = f"[role={role}]" if role else ""
    href = element.get("href", "")
    href_suffix = f" -> {href}" if href else ""
    name = _element_accessible_name(element)
    return f"{element.name}{class_suffix}{role_suffix} -> {name}{href_suffix}"


def _print_focus_report(root: Path, html_files: List[Path]) -> None:
    print("\nFocus order report:")
    for html_path in html_files:
        html = html_path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        focusable = [element for element in soup.find_all(True) if _is_focusable(element)]
        page_label = html_path.relative_to(root).as_posix()
        print(f"\n{page_label} ({len(focusable)} focusable item(s))")
        for index, element in enumerate(focusable, 1):
            print(f"  {index}. {_focusable_description(element)}")


def run_checks(build_dir: str = config.BUILD_DIR, focus_report: bool = False) -> bool:
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

    for required_file in ("robots.txt",):
        if not (root / required_file).is_file():
            errors.append(f"missing required file: {required_file}")
    errors.extend(_check_xml_file(root, config.SITEMAP_FILE, "urlset"))
    errors.extend(_check_xml_file(root, config.RSS_FILE, "rss"))
    errors.extend(_check_xml_file(root, config.ATOM_FILE, "feed"))

    _print_category_summary(errors, warnings)
    _print_grouped_messages(WARNING_PREFIX, warnings)
    _print_grouped_messages(ERROR_PREFIX, errors)

    if focus_report:
        _print_focus_report(root, html_files)

    if errors:
        print(f"Site health check failed: {len(errors)} error(s), {len(warnings)} warning(s).")
        return False

    print(f"Site health check passed: {len(html_files)} HTML page(s), {len(warnings)} warning(s).")
    return True


if __name__ == "__main__":
    arg_parser = ArgumentParser(description="Run post-build checks for the generated static site.")
    arg_parser.add_argument("build_dir", nargs="?", default=config.BUILD_DIR, help="Build directory to inspect.")
    arg_parser.add_argument("--focus-report", action="store_true", help="Print focusable elements in DOM order for manual keyboard review.")
    args = arg_parser.parse_args()
    raise SystemExit(0 if run_checks(args.build_dir, focus_report=args.focus_report) else 1)
