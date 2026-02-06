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

# Directory containing static assets (CSS, JS, SVG) shipped alongside this script
_ASSETS_DIR = Path(__file__).resolve().parent / "assets"


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


def _load_asset(filename: str) -> str:
    """Read a static asset file from the assets directory."""
    path = _ASSETS_DIR / filename
    return path.read_text(encoding="utf-8")


def get_nvidia_logo_svg() -> str:
    """Return the NVIDIA logo SVG with the 'nvidia-logo' class attribute."""
    svg = _load_asset("nvidia-logo.svg").strip()
    # Inject the CSS class so the logo is styled correctly
    return svg.replace("<svg ", '<svg class="nvidia-logo" ', 1)


def get_css() -> str:
    """Return the complete CSS for the wiki site (loaded from assets/wiki.css)."""
    return _load_asset("wiki.css")


def get_search_script(search_index_json: str, base_prefix: str = "") -> str:
    """Return the JavaScript for client-side search.

    *base_prefix* is prepended to search-result URLs so that pages in
    subdirectories link correctly (e.g. ``../`` for a page one level deep).
    """
    search_js = _load_asset("search.js")
    # Inject the search index and base prefix as globals before the IIFE
    return (
        "<script>\n"
        f"window.__wikiSearchIndex = {search_index_json};\n"
        f'window.__wikiBasePrefix = "{base_prefix}";\n'
        f"{search_js}\n"
        "</script>"
    )


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

    # Load static assets
    css = get_css()
    logo_svg = get_nvidia_logo_svg()
    lightbox_js = _load_asset("mermaid-lightbox.js")
    home_href = relative_href(current_html, "index.html")

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {project_title}</title>
    <style>{css}</style>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ startOnLoad: true }});
      await mermaid.run();
    </script>
</head>
<body>
    <header class="top-bar">
        <a class="top-bar-brand" href="{home_href}">
            {logo_svg}
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
{lightbox_js}
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
