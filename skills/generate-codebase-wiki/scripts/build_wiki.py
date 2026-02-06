#!/usr/bin/env python3
"""
build_wiki.py - Universal static wiki generator from Markdown files.

Converts a directory of Markdown files (including subdirectories) into a
static HTML wiki site with hierarchical navigation, breadcrumbs,
table-of-contents, client-side search, and Mermaid diagram support.

Works with any repository / project structure. Pages are auto-discovered
from the input directory, titles are extracted from Markdown headings,
and navigation is generated dynamically.

Supports two layouts:
  - Flat: all .md files in one directory (suitable for small projects)
  - Hierarchical: .md files organised into subdirectories + a JSON config
    that defines sections/subsections (suitable for large projects)

Usage:
    python build_wiki.py [OPTIONS]

Examples:
    # Basic - convert ./wiki/*.md -> ./wiki/*.html
    python build_wiki.py

    # Specify directories and project name
    python build_wiki.py -i docs/ -o site/ --title "My Project Wiki"

    # Use a config file for hierarchical page ordering
    python build_wiki.py -i wiki/ --config wiki.json
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Markdown -> HTML conversion (lightweight, no external dependencies)
# ---------------------------------------------------------------------------


def simple_md_to_html(md_content: str) -> str:
    """Convert Markdown content to HTML (subset parser, no dependencies)."""
    html = md_content

    # Escape HTML characters first
    html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Restore <details> / <summary> blocks (commonly used in wiki pages)
    for tag in ("details", "summary"):
        html = html.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        html = html.replace(f"&lt;/{tag}&gt;", f"</{tag}>")

    # Headers — also inject anchors for TOC linking
    def _heading_replacer(level):
        def _replacer(match):
            text = match.group(1).strip()
            anchor = re.sub(r"[^\w\s-]", "", text.lower())
            anchor = re.sub(r"\s+", "-", anchor).strip("-")
            return f'<h{level} id="{anchor}">{text}</h{level}>'

        return _replacer

    html = re.sub(r"^#### (.+)$", _heading_replacer(4), html, flags=re.MULTILINE)
    html = re.sub(r"^### (.+)$", _heading_replacer(3), html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", _heading_replacer(2), html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", _heading_replacer(1), html, flags=re.MULTILINE)

    # Horizontal rules
    html = re.sub(r"^---+$", "<hr>", html, flags=re.MULTILINE)

    # Bold & italic
    html = re.sub(r"\*\*\*(.*?)\*\*\*", r"<strong><em>\1</em></strong>", html)
    html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)

    # Links — rewrite .md hrefs to .html
    def _link_replacer(match):
        text = match.group(1)
        href = match.group(2)
        if href.endswith(".md"):
            href = href[:-3] + ".html"
        elif ".md#" in href:
            href = href.replace(".md#", ".html#")
        return f'<a href="{href}">{text}</a>'

    html = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", _link_replacer, html)

    # Images
    html = re.sub(r"!\[([^\]]*)\]\(([^\)]+)\)", r'<img src="\2" alt="\1">', html)

    # Unordered lists
    html = re.sub(r"^\* (.+)$", r"<ul><li>\1</li></ul>", html, flags=re.MULTILINE)
    html = re.sub(r"^- (.+)$", r"<ul><li>\1</li></ul>", html, flags=re.MULTILINE)
    html = html.replace("</ul>\n<ul>", "\n")

    # Ordered lists (basic)
    html = re.sub(r"^\d+\. (.+)$", r"<ol><li>\1</li></ol>", html, flags=re.MULTILINE)
    html = html.replace("</ol>\n<ol>", "\n")

    # Blockquotes
    html = re.sub(
        r"^&gt; (.+)$", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE
    )
    html = html.replace("</blockquote>\n<blockquote>", "\n")

    # Fenced code blocks (with language class / mermaid support)
    def _code_block_replacer(match):
        lang = match.group(1) or ""
        code = match.group(2)
        if lang == "mermaid":
            return f'<div class="mermaid">{code}</div>'
        lang_attr = f' class="language-{lang}"' if lang else ""
        return f"<pre><code{lang_attr}>{code}</code></pre>"

    html = re.sub(r"```(\w*)\n([\s\S]*?)```", _code_block_replacer, html)

    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

    # Tables (basic pipe-delimited)
    def _table_replacer(match):
        rows = match.group(0).strip().split("\n")
        table_html = '<div class="table-wrapper"><table>'
        for i, row in enumerate(rows):
            cols = [c.strip() for c in row.strip("|").split("|")]
            # Skip separator row (e.g. |---|---|)
            if i == 1 and all(set(c) <= set("-: ") for c in cols):
                continue
            tag = "th" if i == 0 else "td"
            cells = "".join(f"<{tag}>{col}</{tag}>" for col in cols)
            table_html += f"<tr>{cells}</tr>"
        table_html += "</table></div>"
        return table_html

    html = re.sub(r"\|.*\|\n\|[-:| ]+\|\n(\|.*\|\n?)+", _table_replacer, html)

    return html


# ---------------------------------------------------------------------------
# Table of Contents extraction
# ---------------------------------------------------------------------------


def extract_toc(md_content: str) -> list[dict]:
    """Extract headings from Markdown content for table-of-contents generation."""
    toc = []
    for match in re.finditer(r"^(#{2,4})\s+(.+)$", md_content, re.MULTILINE):
        level = len(match.group(1))
        text = match.group(2).strip()
        anchor = re.sub(r"[^\w\s-]", "", text.lower())
        anchor = re.sub(r"\s+", "-", anchor).strip("-")
        toc.append({"level": level, "text": text, "anchor": anchor})
    return toc


def build_toc_html(toc: list[dict]) -> str:
    """Generate HTML for the page table of contents."""
    if not toc:
        return ""
    items = []
    for entry in toc:
        indent = (entry["level"] - 2) * 14  # indent sub-headings
        items.append(
            f'<a href="#{entry["anchor"]}" class="toc-item" '
            f'style="padding-left:{indent}px">{entry["text"]}</a>'
        )
    return "\n            ".join(items)


# ---------------------------------------------------------------------------
# Page discovery & metadata
# ---------------------------------------------------------------------------


def extract_title(md_content: str, fallback: str) -> str:
    """Extract the first H1 heading from Markdown content as the page title."""
    match = re.search(r"^#\s+(.+)$", md_content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return fallback


def extract_text_content(md_content: str) -> str:
    """Extract plain text from Markdown for search indexing."""
    text = re.sub(r"```[\s\S]*?```", "", md_content)  # remove code blocks
    text = re.sub(r"[#*`\[\]\(\)|>-]", " ", text)  # remove markdown syntax
    text = re.sub(r"\s+", " ", text).strip()
    return text


def slugify(name: str) -> str:
    """Turn a filename stem into a URL-friendly slug."""
    return re.sub(r"[^\w-]", "-", name.lower()).strip("-")


def _resolve_page(
    stem_or_path: str, md_files: dict[str, Path]
) -> tuple[str, Path] | None:
    """Resolve a config page entry to a (key, Path) pair."""
    # Try exact path first (e.g. "modules/auth-module")
    clean = stem_or_path.replace(".md", "")
    if clean in md_files:
        return clean, md_files[clean]
    # Try just the stem (basename without directory)
    stem = Path(clean).stem
    if stem in md_files:
        return stem, md_files[stem]
    return None


def discover_pages(
    input_dir: str, config: dict | None = None
) -> tuple[list[dict], list[dict] | None]:
    """
    Discover Markdown pages in *input_dir* (recursively) and return:
      - An ordered list of page metadata dicts
      - A list of section dicts for hierarchical nav (or None for flat nav)

    Page dict keys: md_path, html_name, title, slug, rel_path, section_path
    Section dict keys: title, pages (list of slugs), subsections (list of section dicts)
    """
    input_path = Path(input_dir)
    md_files: dict[str, Path] = {}

    # Recursively discover all .md files
    for p in sorted(input_path.rglob("*.md")):
        # Use relative path (without extension) as the key
        rel = p.relative_to(input_path)
        key = str(rel.with_suffix(""))
        md_files[key] = p

    pages: list[dict] = []
    seen: set[str] = set()
    sections: list[dict] | None = None

    def _make_page(key: str, md_path: Path, title_override: str | None = None) -> dict:
        content = md_path.read_text(encoding="utf-8")
        rel = md_path.relative_to(input_path)
        html_name = str(rel.with_suffix(".html"))
        title = title_override or extract_title(content, md_path.stem)
        slug = slugify(key)
        section_path = str(rel.parent) if str(rel.parent) != "." else ""
        return {
            "md_path": md_path,
            "html_name": html_name,
            "title": title,
            "slug": slug,
            "rel_path": str(rel),
            "section_path": section_path,
        }

    def _process_section_config(section_cfg: dict) -> dict:
        """Process a section from config and return a section dict with page slugs."""
        section = {
            "title": section_cfg.get("title", "Untitled"),
            "pages": [],
            "subsections": [],
        }

        for entry in section_cfg.get("pages", []):
            if isinstance(entry, str):
                stem = entry.replace(".md", "")
                title_override = None
            else:
                stem = entry["file"].replace(".md", "")
                title_override = entry.get("title")

            resolved = _resolve_page(stem, md_files)
            if resolved:
                key, md_path = resolved
                if key not in seen:
                    page = _make_page(key, md_path, title_override)
                    pages.append(page)
                    section["pages"].append(page["slug"])
                    seen.add(key)
            else:
                print(f"Warning: config references '{stem}.md' but file not found")

        for sub_cfg in section_cfg.get("subsections", []):
            section["subsections"].append(_process_section_config(sub_cfg))

        return section

    # --- Process config ---
    if config:
        # Hierarchical config (sections key)
        if "sections" in config:
            sections = []
            for section_cfg in config["sections"]:
                sections.append(_process_section_config(section_cfg))

        # Flat config (pages key only)
        elif "pages" in config:
            for entry in config["pages"]:
                if isinstance(entry, str):
                    stem = entry.replace(".md", "")
                    title_override = None
                else:
                    stem = entry["file"].replace(".md", "")
                    title_override = entry.get("title")

                resolved = _resolve_page(stem, md_files)
                if resolved:
                    key, md_path = resolved
                    if key not in seen:
                        pages.append(_make_page(key, md_path, title_override))
                        seen.add(key)
                else:
                    print(f"Warning: config references '{stem}.md' but file not found")

    # Append any remaining .md files not covered by config
    for key, md_path in md_files.items():
        if key in seen:
            continue
        pages.append(_make_page(key, md_path))

    # --- Auto-generate sections from directory structure ---
    # If no sections were defined by config, group pages by their subdirectory.
    if sections is None and any(p["section_path"] for p in pages):
        sections = []
        dir_groups: dict[str, list[str]] = {}  # dir_name -> [slug, ...]
        root_slugs: list[str] = []

        for page in pages:
            if page["section_path"]:
                dir_name = page["section_path"]
                dir_groups.setdefault(dir_name, []).append(page["slug"])
            else:
                root_slugs.append(page["slug"])

        # Root-level pages first (as a section if there are other sections)
        if root_slugs and dir_groups:
            sections.append(
                {
                    "title": "Overview",
                    "pages": root_slugs,
                    "subsections": [],
                }
            )

        # Each subdirectory becomes a section
        for dir_name in sorted(dir_groups.keys()):
            # Prettify directory name: "api" -> "API", "core-services" -> "Core Services"
            pretty = dir_name.replace("-", " ").replace("_", " ")
            # All-lowercase short names -> uppercase; otherwise title-case
            if len(pretty) <= 4 and pretty.isalpha():
                pretty = pretty.upper()
            else:
                pretty = pretty.title()
            sections.append(
                {
                    "title": pretty,
                    "pages": dir_groups[dir_name],
                    "subsections": [],
                }
            )

        # If only root-level pages exist (no subdirs), keep sections as None
        if not dir_groups:
            sections = None

    return pages, sections


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------


def relative_href(from_html: str, to_html: str) -> str:
    """Compute the relative URL from one HTML page to another.

    Both paths are relative to the wiki output root.
    Example: relative_href("modules/auth.html", "overview.html") -> "../overview.html"
    """
    from_parts = Path(from_html).parent.parts
    to_path = Path(to_html)
    prefix = "/".join([".."] * len(from_parts)) if from_parts else ""
    if prefix:
        return f"{prefix}/{to_path}"
    return str(to_path)


def build_flat_nav_html(pages: list[dict], active_slug: str, current_html: str) -> str:
    """Generate a flat sidebar navigation HTML."""
    items: list[str] = []
    for page in pages:
        active = ' class="active"' if page["slug"] == active_slug else ""
        href = relative_href(current_html, page["html_name"])
        items.append(f'<li><a href="{href}"{active}>{page["title"]}</a></li>')
    return "\n            ".join(items)


def build_hierarchical_nav_html(
    sections: list[dict], pages: list[dict], active_slug: str, current_html: str
) -> str:
    """Generate hierarchical sidebar navigation with collapsible sections."""
    page_map = {p["slug"]: p for p in pages}

    def _render_section(section: dict, depth: int = 0) -> str:
        # Check if active page is in this section (including subsections)
        def _contains_active(sec: dict) -> bool:
            if active_slug in sec["pages"]:
                return True
            return any(_contains_active(sub) for sub in sec.get("subsections", []))

        is_open = _contains_active(section)
        open_attr = " open" if is_open else ""
        indent = "  " * depth

        html = f'{indent}<li class="nav-section">\n'
        html += f"{indent}  <details{open_attr}>\n"
        html += f'{indent}    <summary class="nav-section-title">{section["title"]}</summary>\n'
        html += f'{indent}    <ul class="nav-section-pages">\n'

        for slug in section["pages"]:
            if slug in page_map:
                page = page_map[slug]
                active = ' class="active"' if slug == active_slug else ""
                href = relative_href(current_html, page["html_name"])
                html += (
                    f'{indent}      <li><a href="{href}"{active}>'
                    f"{page['title']}</a></li>\n"
                )

        for sub in section.get("subsections", []):
            html += _render_section(sub, depth + 1)

        html += f"{indent}    </ul>\n"
        html += f"{indent}  </details>\n"
        html += f"{indent}</li>\n"
        return html

    items = []
    for section in sections:
        items.append(_render_section(section))

    # Render any pages not in sections
    sectioned_slugs = set()

    def _collect_slugs(sec):
        sectioned_slugs.update(sec["pages"])
        for sub in sec.get("subsections", []):
            _collect_slugs(sub)

    for sec in sections:
        _collect_slugs(sec)

    for page in pages:
        if page["slug"] not in sectioned_slugs:
            active = ' class="active"' if page["slug"] == active_slug else ""
            href = relative_href(current_html, page["html_name"])
            items.append(f'<li><a href="{href}"{active}>{page["title"]}</a></li>\n')

    return "".join(items)


def build_breadcrumbs(page: dict, sections: list[dict] | None) -> str:
    """Generate breadcrumb navigation HTML for a page."""
    if not sections:
        return ""

    # Find the section path to this page
    path: list[str] = []

    def _find_in_sections(secs: list[dict], slug: str, trail: list[str]) -> bool:
        for sec in secs:
            current_trail = trail + [sec["title"]]
            if slug in sec["pages"]:
                path.extend(current_trail)
                return True
            if _find_in_sections(sec.get("subsections", []), slug, current_trail):
                return True
        return False

    _find_in_sections(sections, page["slug"], [])

    if not path:
        return ""

    home_icon = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">'
        '<path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 '
        "001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 "
        '001.414-1.414l-7-7z"/></svg>'
    )
    crumbs = [f'<span class="breadcrumb-home">{home_icon}</span>']
    for part in path:
        crumbs.append('<span class="breadcrumb-sep">&rsaquo;</span>')
        crumbs.append(f'<span class="breadcrumb-item">{part}</span>')
    crumbs.append('<span class="breadcrumb-sep">&rsaquo;</span>')
    crumbs.append(
        f'<span class="breadcrumb-item breadcrumb-current">{page["title"]}</span>'
    )

    return f'<nav class="breadcrumbs">{"".join(crumbs)}</nav>'


def build_search_index(pages: list[dict]) -> str:
    """Build a JavaScript search index from all pages."""
    index = []
    for page in pages:
        content = page["md_path"].read_text(encoding="utf-8")
        text = extract_text_content(content)
        # Truncate to keep index manageable
        text = text[:3000]
        index.append(
            {
                "title": page["title"],
                "url": page["html_name"],
                "text": text,
            }
        )
    return json.dumps(index, ensure_ascii=False)


def get_nvidia_logo_svg() -> str:
    """Return the NVIDIA logo SVG (eye mark + NVIDIA text) for the dark header.

    Colors: eye mark #76b900 (green), NVIDIA text #ffffff (white).
    Based on the official NVIDIA horizontal logo.
    """
    return (
        '<svg class="nvidia-logo" xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 3096.56 1065.98" role="img" aria-label="NVIDIA">'
        '<path fill="#76b900" d="M562.33,440.33V398.81c4-.28,8.1-.5,12.25-.63,'
        "113.55-3.57,188,97.56,188,97.56S682.16,607.49,595.9,607.49a104.51,"
        "104.51,0,0,1-33.57-5.37V476.24c44.21,5.34,53.09,24.86,79.68,69.16"
        "l59.1-49.84S658,439,585.24,439a214.88,214.88,0,0,0-22.91,1.35m0-137.14"
        "v62c4.08-.32,8.16-.58,12.25-.73C732.49,359.15,835.35,494,835.35,494"
        "S717.19,637.65,594.1,637.65a181.36,181.36,0,0,1-31.77-2.8v38.33a208.94,"
        "208.94,0,0,0,26.46,1.72c114.55,0,197.39-58.5,277.62-127.74,13.29,10.65,"
        "67.74,36.55,78.94,47.91-76.28,63.85-254,115.31-354.8,115.31-9.71,0-19-"
        ".58-28.22-1.46v53.87H997.74V303.19Zm0,298.93v32.73C456.38,616,427,505.83,"
        "427,505.83s50.87-56.37,135.36-65.5v35.91l-.16,0c-44.34-5.33-79,36.1-79,"
        "36.1s19.41,69.73,79.14,89.8M374.15,501.05S437,408.39,562.33,398.81V365.2"
        "C423.46,376.35,303.19,494,303.19,494S371.3,690.89,562.33,708.92V673.18"
        'C422.15,655.55,374.15,501.05,374.15,501.05Z"/>'
        '<path fill="#000" d="M1782,390l0,301.68h85.2V390Zm-670.22-.41V691.71h86'
        "V462.33l66.59,0c22.06,0,37.77,5.48,48.4,16.83,13.48,14.36,19,37.51,19,"
        "79.87V691.71l83.27,0V524.81c0-119.12-75.93-135.19-150.21-135.19h-153"
        "m807.4.43V691.71h138.19c73.63,0,97.66-12.25,123.65-39.7,18.37-19.27,"
        "30.24-61.58,30.24-107.82,0-42.4-10.05-80.23-27.58-103.78-31.56-42.13-77"
        "-50.36-144.92-50.36Zm84.52,65.68h36.63c53.14,0,87.51,23.87,87.51,85.79"
        "s-34.37,85.8-87.51,85.8h-36.63Zm-344.54-65.68-71.1,239.08-68.14-239.07"
        "h-92l97.31,301.66h122.79l98.07-301.66Zm591.74,301.66h85.21V390.06h-85.23"
        "Zm238.84-301.56-119,301.46h84l18.82-53.29h140.8l17.82,53.29h91.21"
        'L2603.56,390.13Zm55.31,55,51.61,141.23H2491.82Z"/>'
        "</svg>"
    )


def get_css() -> str:
    """Return the complete CSS for the wiki site (NVIDIA-docs inspired)."""
    return """
        * { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --header-height: 48px;
            --sidebar-width: 260px;
            --toc-width: 230px;
            --accent: #76b900;
            --accent-hover: #85d100;
            --accent-bg: #f0f8e0;
            --bg: #ffffff;
            --sidebar-bg: #ffffff;
            --header-bg: #ffffff;
            --header-text: #1a1a1a;
            --border: #e0e0e0;
            --border-light: #eeeeee;
            --text: #1a1a1a;
            --text-secondary: #616161;
            --text-tertiary: #888888;
            --code-bg: #f5f5f5;
            --code-border: #e0e0e0;
            --link: #1976d2;
            --link-hover: #1565c0;
            --callout-bg: #f8fdf0;
            --callout-border: #76b900;
        }

        html { scroll-behavior: smooth; }
        body {
            font-family: "NVIDIA Sans", -apple-system, BlinkMacSystemFont, "Segoe UI",
                         Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.7; color: var(--text); background: var(--bg);
            display: flex; flex-direction: column; min-height: 100vh;
        }

        /* ==================== Top Header Bar ==================== */
        header.top-bar {
            height: var(--header-height); background: var(--header-bg);
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 24px; position: sticky; top: 0; z-index: 200;
            border-bottom: 1px solid var(--border);
            flex-shrink: 0;
        }
        .top-bar-brand {
            display: flex; align-items: center; gap: 14px;
            color: var(--header-text); text-decoration: none;
        }
        .top-bar-brand:hover { text-decoration: none; }
        .nvidia-logo { height: 48px; width: auto; display: block; }
        .top-bar-title {
            font-size: 20px; font-weight: 700; color: var(--text);
            border-left: 1px solid var(--border); padding-left: 14px;
        }
        .top-bar-actions { display: flex; align-items: center; gap: 16px; }

        /* Top-bar search */
        .topbar-search { position: relative; }
        .topbar-search-input {
            width: 220px; padding: 5px 32px 5px 10px;
            border: 1px solid var(--border); border-radius: 4px;
            background: var(--bg); color: var(--text); font-size: 0.82em;
            outline: none; transition: border-color 0.2s, width 0.2s;
        }
        .topbar-search-input::placeholder { color: var(--text-tertiary); }
        .topbar-search-input:focus {
            border-color: var(--accent); width: 300px;
            box-shadow: 0 0 0 3px rgba(118,185,0,0.12);
        }
        .topbar-search-icon {
            position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
            color: var(--text-tertiary); font-size: 0.85em; pointer-events: none;
        }
        .search-results {
            position: absolute; top: calc(100% + 4px); right: 0; width: 420px;
            background: var(--bg); border: 1px solid var(--border);
            border-radius: 6px; max-height: 400px; overflow-y: auto;
            z-index: 300; display: none;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        }
        .search-results.visible { display: block; }
        .search-result-item {
            display: block; padding: 10px 14px; text-decoration: none;
            color: var(--text); border-bottom: 1px solid var(--border-light);
            font-size: 0.85em; transition: background 0.1s;
        }
        .search-result-item:last-child { border-bottom: none; }
        .search-result-item:hover { background: var(--accent-bg); }
        .search-result-title { font-weight: 600; color: var(--text); }
        .search-result-snippet {
            color: var(--text-secondary); font-size: 0.88em; margin-top: 3px;
            line-height: 1.4;
        }
        .search-no-results {
            padding: 16px; color: var(--text-secondary); font-size: 0.85em;
            text-align: center;
        }

        /* ==================== Layout Container ==================== */
        .layout {
            display: flex; flex: 1;
            min-height: calc(100vh - var(--header-height));
        }

        /* ==================== Left Sidebar ==================== */
        nav.sidebar {
            width: var(--sidebar-width); min-width: var(--sidebar-width);
            padding: 20px 0; background: var(--sidebar-bg);
            border-right: 1px solid var(--border);
            height: calc(100vh - var(--header-height));
            position: sticky; top: var(--header-height);
            overflow-y: auto; overflow-x: hidden;
            display: flex; flex-direction: column;
        }
        .sidebar-label {
            font-size: 0.72em; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.08em; color: var(--text-tertiary);
            padding: 0 20px; margin-bottom: 10px;
        }

        /* Nav tree */
        nav.sidebar ul { list-style: none; padding: 0; margin: 0; }
        nav.sidebar li { margin: 0; }
        nav.sidebar > ul > li > a,
        nav.sidebar > ul > li.nav-section {
            /* top-level items get a subtle separator */
        }
        nav.sidebar a {
            color: var(--text); text-decoration: none; display: block;
            padding: 5px 20px; font-size: 0.84em; line-height: 1.5;
            border-left: 3px solid transparent;
            transition: background 0.12s, border-color 0.12s;
        }
        nav.sidebar a:hover {
            background: #f5f5f5; text-decoration: none;
        }
        nav.sidebar a.active {
            color: var(--text); font-weight: 600;
            border-left: 3px solid var(--accent);
            background: var(--accent-bg);
        }

        /* Section grouping */
        .nav-section { margin: 2px 0; }
        .nav-section details { border: none; padding: 0; margin: 0; background: none; }
        .nav-section summary.nav-section-title {
            cursor: pointer; font-weight: 600; font-size: 0.84em;
            color: var(--text); padding: 6px 20px; list-style: none;
            display: flex; align-items: center; gap: 6px;
            border-left: 3px solid transparent;
            transition: background 0.12s;
            user-select: none;
        }
        .nav-section summary.nav-section-title::-webkit-details-marker { display: none; }
        .nav-section summary.nav-section-title::before {
            content: ""; display: inline-block;
            width: 0; height: 0;
            border-left: 5px solid var(--text-secondary);
            border-top: 4px solid transparent;
            border-bottom: 4px solid transparent;
            transition: transform 0.15s;
            flex-shrink: 0;
        }
        .nav-section details[open] > summary.nav-section-title::before {
            transform: rotate(90deg);
        }
        .nav-section summary.nav-section-title:hover { background: #f5f5f5; }
        .nav-section-pages { padding-left: 12px !important; }

        /* ==================== Main Content ==================== */
        main {
            flex: 1; padding: 28px 48px 60px; min-width: 0;
        }

        /* Breadcrumbs */
        .breadcrumbs {
            font-size: 0.8em; color: var(--text-secondary); margin-bottom: 20px;
            display: flex; align-items: center; flex-wrap: wrap; gap: 2px;
        }
        .breadcrumb-home {
            display: inline-flex; align-items: center; color: var(--text-secondary);
            text-decoration: none;
        }
        .breadcrumb-home:hover { color: var(--accent); }
        .breadcrumb-home svg { width: 14px; height: 14px; }
        .breadcrumb-sep { margin: 0 4px; color: var(--text-tertiary); font-size: 0.85em; }
        .breadcrumb-item { color: var(--text-secondary); }
        .breadcrumb-current { color: var(--text); font-weight: 500; }

        /* Typography */
        h1 {
            font-size: 1.85em; font-weight: 700; color: var(--text);
            margin: 0 0 16px 0; padding: 0; line-height: 1.25;
            border: none;
        }
        h2 {
            font-size: 1.35em; font-weight: 700; color: var(--text);
            margin: 36px 0 12px; padding: 0; line-height: 1.3;
            border: none;
        }
        h3 {
            font-size: 1.1em; font-weight: 600; color: var(--text);
            margin: 28px 0 8px;
        }
        h4 {
            font-size: 0.95em; font-weight: 600; color: var(--text);
            margin: 20px 0 6px;
        }
        p { margin: 0 0 14px; }

        /* Inline code */
        code {
            background-color: var(--code-bg); padding: 0.15em 0.45em;
            border-radius: 3px; border: 1px solid var(--code-border);
            font-family: "SF Mono", "Fira Code", "Fira Mono", "Roboto Mono",
                         Menlo, Consolas, "Liberation Mono", monospace;
            font-size: 0.85em; color: #c7254e;
        }

        /* Code blocks */
        pre {
            background-color: #263238; color: #eeffff;
            padding: 16px 20px; border-radius: 6px;
            overflow-x: auto; line-height: 1.5; margin: 16px 0;
            font-size: 0.85em;
        }
        pre code {
            background: none; padding: 0; border: none;
            font-size: 1em; color: inherit;
        }
        pre strong, pre b {
            display: block; color: #80cbc4; font-weight: 700;
            font-size: 1.1em; margin-top: 12px;
            padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.12);
        }
        pre strong:first-child, pre b:first-child,
        pre code > strong:first-child, pre code > b:first-child {
            margin-top: 0; padding-top: 0; border-top: none;
        }
        pre h1, pre h2, pre h3, pre h4, pre h5, pre h6 {
            color: #ffcc80; font-weight: 700; margin: 14px 0 6px;
            border: none; padding: 0;
        }
        pre h1 { font-size: 1.3em; color: #ffe082; }
        pre h2 { font-size: 1.15em; }
        pre h3 { font-size: 1.05em; }

        /* Tables */
        .table-wrapper { overflow-x: auto; margin: 16px 0; }
        table { border-collapse: collapse; width: 100%; font-size: 0.9em; }
        th, td {
            border: 1px solid var(--border); padding: 10px 14px; text-align: left;
        }
        th {
            background: #f7f7f7; font-weight: 600; color: var(--text);
            font-size: 0.9em;
        }
        td { color: var(--text); }
        tr:nth-child(even) td { background: #fafafa; }

        /* Blockquotes / callouts */
        blockquote {
            border-left: 4px solid var(--callout-border);
            background: var(--callout-bg); color: var(--text);
            padding: 12px 16px; margin: 16px 0;
            border-radius: 0 6px 6px 0; font-size: 0.92em;
        }

        /* Details / Summary */
        details {
            border: 1px solid var(--border); border-radius: 6px;
            padding: 14px 16px; margin-bottom: 16px; background: #fafafa;
        }
        details[open] { background: var(--bg); }
        summary { cursor: pointer; font-weight: 600; font-size: 0.92em; }

        /* Links */
        main a { color: var(--link); text-decoration: none; }
        main a:hover { color: var(--link-hover); text-decoration: underline; }

        /* Images */
        img { max-width: 100%; height: auto; border-radius: 4px; }
        hr { border: none; border-top: 1px solid var(--border); margin: 28px 0; }

        /* Lists */
        ul, ol { margin: 0 0 14px 0; padding-left: 24px; }
        li { margin-bottom: 4px; }
        li > ul, li > ol { margin-top: 4px; margin-bottom: 0; }

        /* Mermaid diagrams */
        .mermaid {
            margin: 24px 0; text-align: center;
            background: #fafafa; border-radius: 8px; padding: 16px;
            cursor: zoom-in; transition: box-shadow 0.2s;
        }
        .mermaid:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.08); }

        /* Mermaid lightbox overlay */
        .mermaid-overlay {
            display: none; position: fixed; inset: 0; z-index: 9999;
            background: rgba(0,0,0,0.65); backdrop-filter: blur(4px);
            align-items: center; justify-content: center; cursor: zoom-out;
        }
        .mermaid-overlay.visible { display: flex; }
        .mermaid-overlay-content {
            background: #fff; border-radius: 12px; padding: 32px;
            width: 90vw; height: 88vh; overflow: hidden;
            box-shadow: 0 12px 48px rgba(0,0,0,0.25);
            display: flex; align-items: center; justify-content: center;
            cursor: grab; position: relative;
        }
        .mermaid-overlay-content svg {
            display: block; width: 100%; height: auto; max-height: 85vh;
            transform-origin: center center;
        }

        /* ==================== Right TOC ("On this page") ==================== */
        aside.toc {
            width: var(--toc-width); min-width: var(--toc-width);
            padding: 28px 16px 28px 20px;
            height: calc(100vh - var(--header-height));
            position: sticky; top: var(--header-height);
            overflow-y: auto; font-size: 0.8em;
            border-left: 1px solid var(--border-light);
        }
        .toc-title {
            font-weight: 700; color: var(--text); font-size: 0.85em;
            margin-bottom: 12px; letter-spacing: 0.02em;
        }
        .toc-item {
            display: block; color: var(--text-secondary); text-decoration: none;
            padding: 4px 0 4px 10px; margin: 0;
            border-left: 2px solid transparent;
            line-height: 1.5; transition: color 0.12s, border-color 0.12s;
        }
        .toc-item:hover {
            color: var(--accent); border-left-color: var(--accent);
            text-decoration: none;
        }

        /* ==================== Responsive ==================== */
        @media (max-width: 1200px) {
            aside.toc { display: none; }
        }
        @media (max-width: 768px) {
            header.top-bar { padding: 0 16px; }
            .topbar-search-input { width: 160px; }
            .topbar-search-input:focus { width: 200px; }
            .layout { flex-direction: column; }
            nav.sidebar {
                width: 100%; height: auto; position: relative;
                border-right: none; border-bottom: 1px solid var(--border);
                min-width: unset; top: 0;
            }
            main { padding: 20px 16px; }
        }
"""


def get_search_script(search_index_json: str, base_prefix: str = "") -> str:
    """Return the JavaScript for client-side search.

    *base_prefix* is prepended to search-result URLs so that pages in
    subdirectories link correctly (e.g. ``../`` for a page one level deep).
    """
    return f"""
    <script>
    (function() {{
      var searchIndex = {search_index_json};
      var basePrefix = "{base_prefix}";
      var input = document.getElementById('wiki-search');
      var results = document.getElementById('search-results');
      if (!input || !results) return;

      input.addEventListener('input', function() {{
        var q = this.value.trim().toLowerCase();
        if (q.length < 2) {{ results.className = 'search-results'; results.innerHTML = ''; return; }}

        var matches = [];
        for (var i = 0; i < searchIndex.length; i++) {{
          var page = searchIndex[i];
          var titleMatch = page.title.toLowerCase().indexOf(q) !== -1;
          var textMatch = page.text.toLowerCase().indexOf(q) !== -1;
          if (titleMatch || textMatch) {{
            var snippet = '';
            if (textMatch) {{
              var idx = page.text.toLowerCase().indexOf(q);
              var start = Math.max(0, idx - 40);
              var end = Math.min(page.text.length, idx + q.length + 60);
              snippet = (start > 0 ? '...' : '') + page.text.substring(start, end) + (end < page.text.length ? '...' : '');
            }}
            matches.push({{ title: page.title, url: basePrefix + page.url, snippet: snippet, titleMatch: titleMatch }});
          }}
        }}

        matches.sort(function(a, b) {{ return (b.titleMatch ? 1 : 0) - (a.titleMatch ? 1 : 0); }});

        if (matches.length === 0) {{
          results.innerHTML = '<div class="search-no-results">No results found</div>';
        }} else {{
          var html = '';
          for (var j = 0; j < Math.min(matches.length, 10); j++) {{
            var m = matches[j];
            html += '<a class="search-result-item" href="' + m.url + '">';
            html += '<div class="search-result-title">' + m.title + '</div>';
            if (m.snippet) html += '<div class="search-result-snippet">' + m.snippet + '</div>';
            html += '</a>';
          }}
          results.innerHTML = html;
        }}
        results.className = 'search-results visible';
      }});

      document.addEventListener('click', function(e) {{
        if (!results.contains(e.target) && e.target !== input) {{
          results.className = 'search-results';
        }}
      }});

      input.addEventListener('focus', function() {{
        if (this.value.trim().length >= 2) results.className = 'search-results visible';
      }});
    }})();
    </script>
    """


def render_page(
    md_content: str,
    title: str,
    pages: list[dict],
    active_slug: str,
    project_title: str,
    lang: str,
    sections: list[dict] | None,
    current_page: dict,
    search_index_json: str,
) -> str:
    """Render a full HTML page with sidebar, breadcrumbs, TOC, and search."""
    current_html = current_page["html_name"]

    # Navigation
    if sections:
        nav_html = build_hierarchical_nav_html(
            sections, pages, active_slug, current_html
        )
    else:
        nav_html = build_flat_nav_html(pages, active_slug, current_html)

    # Breadcrumbs
    breadcrumbs_html = build_breadcrumbs(current_page, sections)

    # Table of contents
    toc = extract_toc(md_content)
    toc_html = build_toc_html(toc)

    # Body content
    body_html = simple_md_to_html(md_content)

    # Search script — compute path prefix for relative URLs
    depth = len(Path(current_html).parent.parts)
    search_base_prefix = "/".join([".."] * depth) + "/" if depth > 0 else ""
    search_script = get_search_script(search_index_json, search_base_prefix)

    # TOC sidebar
    toc_aside = ""
    if toc_html:
        toc_aside = f"""
        <aside class="toc">
            <div class="toc-title">On this page</div>
            {toc_html}
        </aside>"""

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {project_title}</title>
    <style>{get_css()}</style>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ startOnLoad: true }});
      // After mermaid renders, mark rendered containers for lightbox
      await mermaid.run();
      document.querySelectorAll('.mermaid[data-processed]').forEach(function(el) {{
        el.dataset.lightbox = 'true';
      }});
    </script>
</head>
<body>
    <header class="top-bar">
        <a class="top-bar-brand" href="{relative_href(current_html, "index.html")}">
            {get_nvidia_logo_svg()}
            <span class="top-bar-title">{project_title}</span>
        </a>
        <div class="top-bar-actions">
            <div class="topbar-search">
                <input type="text" id="wiki-search" class="topbar-search-input" placeholder="Search docs..." autocomplete="off">
                <span class="topbar-search-icon">&#x1F50D;</span>
                <div id="search-results" class="search-results"></div>
            </div>
        </div>
    </header>
    <div class="layout">
        <nav class="sidebar">
            <div class="sidebar-label">Table of Contents</div>
            <ul>
                {nav_html}
            </ul>
        </nav>
        <main>
            {breadcrumbs_html}
            {body_html}
        </main>{toc_aside}
    </div>
    <div class="mermaid-overlay" id="mermaid-overlay">
        <div class="mermaid-overlay-content" id="mermaid-overlay-content"></div>
    </div>
    {search_script}
    <script>
    (function() {{
      var overlay = document.getElementById('mermaid-overlay');
      var content = document.getElementById('mermaid-overlay-content');
      if (!overlay || !content) return;

      var scale = 1;
      var translateX = 0;
      var translateY = 0;
      var isDragging = false;
      var dragStartX = 0;
      var dragStartY = 0;
      var dragStartTX = 0;
      var dragStartTY = 0;

      function applyTransform() {{
        var svg = content.querySelector('svg');
        if (svg) svg.style.transform = 'translate(' + translateX + 'px,' + translateY + 'px) scale(' + scale + ')';
      }}

      function resetTransform() {{
        scale = 1; translateX = 0; translateY = 0;
      }}

      // Use event delegation so it works even after mermaid replaces DOM nodes
      document.addEventListener('click', function(e) {{
        var target = e.target.closest('.mermaid');
        if (target) {{
          var svg = target.querySelector('svg');
          if (svg) {{
            content.innerHTML = '';
            var clone = svg.cloneNode(true);
            // Ensure viewBox exists so SVG scales properly when we resize it
            if (!clone.getAttribute('viewBox')) {{
              var w = svg.getAttribute('width') || svg.getBoundingClientRect().width;
              var h = svg.getAttribute('height') || svg.getBoundingClientRect().height;
              w = parseFloat(w) || 800;
              h = parseFloat(h) || 600;
              clone.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
            }}
            clone.removeAttribute('width');
            clone.removeAttribute('height');
            clone.removeAttribute('style');
            clone.style.width = '100%';
            clone.style.height = 'auto';
            clone.style.maxHeight = '85vh';
            clone.style.transformOrigin = 'center center';
            clone.style.transition = 'transform 0.15s ease';
            content.appendChild(clone);
            resetTransform();
            overlay.classList.add('visible');
          }}
        }}
      }});

      // Mouse wheel zoom inside the overlay
      content.addEventListener('wheel', function(e) {{
        e.preventDefault();
        var delta = e.deltaY > 0 ? -0.1 : 0.1;
        var newScale = Math.min(Math.max(scale + delta, 0.2), 10);
        // Zoom toward cursor position
        var rect = content.getBoundingClientRect();
        var cx = e.clientX - rect.left - rect.width / 2;
        var cy = e.clientY - rect.top - rect.height / 2;
        var ratio = newScale / scale;
        translateX = cx - ratio * (cx - translateX);
        translateY = cy - ratio * (cy - translateY);
        scale = newScale;
        applyTransform();
      }}, {{ passive: false }});

      // Mouse drag to pan inside the overlay
      content.addEventListener('mousedown', function(e) {{
        if (e.button !== 0) return;
        isDragging = true;
        dragStartX = e.clientX;
        dragStartY = e.clientY;
        dragStartTX = translateX;
        dragStartTY = translateY;
        content.style.cursor = 'grabbing';
        e.preventDefault();
      }});
      document.addEventListener('mousemove', function(e) {{
        if (!isDragging) return;
        translateX = dragStartTX + (e.clientX - dragStartX);
        translateY = dragStartTY + (e.clientY - dragStartY);
        applyTransform();
      }});
      document.addEventListener('mouseup', function() {{
        if (isDragging) {{
          isDragging = false;
          content.style.cursor = '';
        }}
      }});

      // Close overlay when clicking on the backdrop (not on the content)
      overlay.addEventListener('click', function(e) {{
        if (e.target === overlay) {{
          overlay.classList.remove('visible');
          resetTransform();
        }}
      }});
      document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') {{
          overlay.classList.remove('visible');
          resetTransform();
        }}
      }});
    }})();
    </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main build logic
# ---------------------------------------------------------------------------


def load_config(config_path: str | None) -> dict | None:
    """Load optional JSON config file for page ordering and metadata."""
    if not config_path:
        return None
    path = Path(config_path)
    if not path.exists():
        print(f"Warning: config file '{config_path}' not found, ignoring")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_wiki(
    input_dir: str = "wiki",
    output_dir: str | None = None,
    project_title: str = "Codebase Wiki",
    lang: str = "en",
    config: dict | None = None,
) -> None:
    """
    Main entry point: discover pages, convert to HTML, write output.

    Parameters
    ----------
    input_dir : str
        Directory containing .md source files (searched recursively).
    output_dir : str | None
        Directory for generated .html files. Defaults to *input_dir*/html.
    project_title : str
        Title shown in the sidebar header and <title> tag.
    lang : str
        HTML lang attribute (e.g. "en", "zh-CN").
    config : dict | None
        Optional config dict (from JSON) with page ordering / section hierarchy.
    """
    output = Path(output_dir) if output_dir else Path(input_dir) / "html"
    output.mkdir(parents=True, exist_ok=True)

    pages, sections = discover_pages(input_dir, config)
    if not pages:
        print(f"Error: no .md files found in '{input_dir}'")
        sys.exit(1)

    layout = "hierarchical" if sections else "flat"
    print(
        f"Building wiki ({layout} layout): {len(pages)} page(s) from '{input_dir}' -> '{output}'"
    )
    print(f"Project title: {project_title}")
    if sections:
        print(f"Sections: {len(sections)} top-level section(s)")
    print()

    # Build search index once
    search_index_json = build_search_index(pages)

    for page in pages:
        md_content = page["md_path"].read_text(encoding="utf-8")

        html_content = render_page(
            md_content=md_content,
            title=page["title"],
            pages=pages,
            active_slug=page["slug"],
            project_title=project_title,
            lang=lang,
            sections=sections,
            current_page=page,
            search_index_json=search_index_json,
        )

        # Ensure output subdirectories exist
        html_path = output / page["html_name"]
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html_content, encoding="utf-8")
        print(f"  ✓ {page['html_name']:40s}  ({page['title']})")

    # Generate an index.html that redirects to the first page
    if pages:
        first_page = pages[0]["html_name"]
        index_path = output / "index.html"
        index_path.write_text(
            f"<!DOCTYPE html><html><head>"
            f'<meta http-equiv="refresh" content="0;url={first_page}">'
            f'</head><body><a href="{first_page}">Go to wiki</a></body></html>',
            encoding="utf-8",
        )
        print(f"  ✓ {'index.html':40s}  (redirect -> {first_page})")

    print(f"\nDone! Open {output / 'index.html'} in your browser.")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a directory of Markdown files into a static HTML wiki.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                  # ./wiki/*.md -> ./wiki/html/*.html
  %(prog)s -i docs/ -o site/                # docs/*.md   -> site/*.html
  %(prog)s -i wiki/ --title "My Project"    # wiki/*.md   -> wiki/html/*.html
  %(prog)s --config wiki.json               # use config for section hierarchy
        """,
    )
    parser.add_argument(
        "-i",
        "--input",
        default="wiki",
        help="Input directory containing .md files (default: wiki)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output directory for .html files (default: <input>/html)",
    )
    parser.add_argument(
        "--title",
        default="Codebase Wiki",
        help='Project / wiki title (default: "Codebase Wiki")',
    )
    parser.add_argument(
        "--lang",
        default="en",
        help='HTML lang attribute, e.g. "en", "zh-CN" (default: en)',
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a JSON config file for section hierarchy and metadata",
    )

    args = parser.parse_args()

    # Auto-discover wiki.json in input directory if --config not specified
    config_path = args.config
    if not config_path:
        auto_config = Path(args.input) / "wiki.json"
        if auto_config.exists():
            config_path = str(auto_config)
            print(f"Auto-detected config: {config_path}")

    config = load_config(config_path)

    # Config file can also provide defaults for title / lang
    if config:
        if "title" in config and args.title == "Codebase Wiki":
            args.title = config["title"]
        if "lang" in config and args.lang == "en":
            args.lang = config["lang"]

    build_wiki(
        input_dir=args.input,
        output_dir=args.output,
        project_title=args.title,
        lang=args.lang,
        config=config,
    )


if __name__ == "__main__":
    main()
