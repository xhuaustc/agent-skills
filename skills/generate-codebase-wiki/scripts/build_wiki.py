#!/usr/bin/env python3
"""
build_wiki.py - Universal static wiki generator from Markdown files.

Converts a directory of Markdown files into a static HTML wiki site with
navigation sidebar, syntax highlighting, and Mermaid diagram support.

Works with any repository / project structure. Pages are auto-discovered
from the input directory, titles are extracted from Markdown headings,
and navigation is generated dynamically.

Usage:
    python build_wiki.py [OPTIONS]

Examples:
    # Basic - convert ./wiki/*.md -> ./wiki/*.html
    python build_wiki.py

    # Specify directories and project name
    python build_wiki.py -i docs/ -o site/ --title "My Project Wiki"

    # Use a config file for page ordering
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

    # Headers
    html = re.sub(r"^#### (.*$)", r"<h4>\1</h4>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.*$)", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.*$)", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.*$)", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # Horizontal rules
    html = re.sub(r"^---+$", "<hr>", html, flags=re.MULTILINE)

    # Bold & italic
    html = re.sub(r"\*\*\*(.*?)\*\*\*", r"<strong><em>\1</em></strong>", html)
    html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)

    # Links
    html = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r'<a href="\2">\1</a>', html)

    # Images
    html = re.sub(r"!\[([^\]]*)\]\(([^\)]+)\)", r'<img src="\2" alt="\1">', html)

    # Unordered lists
    html = re.sub(r"^\* (.*$)", r"<ul><li>\1</li></ul>", html, flags=re.MULTILINE)
    html = re.sub(r"^- (.*$)", r"<ul><li>\1</li></ul>", html, flags=re.MULTILINE)
    html = html.replace("</ul>\n<ul>", "\n")

    # Ordered lists (basic)
    html = re.sub(r"^\d+\. (.*$)", r"<ol><li>\1</li></ol>", html, flags=re.MULTILINE)
    html = html.replace("</ol>\n<ol>", "\n")

    # Blockquotes
    html = re.sub(
        r"^&gt; (.*$)", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE
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
        table_html = "<table>"
        for i, row in enumerate(rows):
            cols = [c.strip() for c in row.strip("|").split("|")]
            # Skip separator row (e.g. |---|---|)
            if i == 1 and all(set(c) <= set("-: ") for c in cols):
                continue
            tag = "th" if i == 0 else "td"
            cells = "".join(f"<{tag}>{col}</{tag}>" for col in cols)
            table_html += f"<tr>{cells}</tr>"
        table_html += "</table>"
        return table_html

    html = re.sub(r"\|.*\|\n\|[-:| ]+\|\n(\|.*\|\n?)+", _table_replacer, html)

    return html


# ---------------------------------------------------------------------------
# Page discovery & metadata
# ---------------------------------------------------------------------------

def extract_title(md_content: str, fallback: str) -> str:
    """Extract the first H1 heading from Markdown content as the page title."""
    match = re.search(r"^#\s+(.+)$", md_content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return fallback


def slugify(name: str) -> str:
    """Turn a filename stem into a URL-friendly slug."""
    return re.sub(r"[^\w-]", "-", name.lower()).strip("-")


def discover_pages(input_dir: str, config: dict | None = None) -> list[dict]:
    """
    Discover Markdown pages in *input_dir* and return an ordered list of
    page metadata dicts: {md_path, html_name, title, slug}.

    If *config* contains a ``pages`` list, it is used to control ordering and
    titles.  Any .md files not listed in config are appended alphabetically.
    """
    input_path = Path(input_dir)
    md_files: dict[str, Path] = {}
    for p in sorted(input_path.glob("*.md")):
        md_files[p.stem] = p

    pages: list[dict] = []
    seen: set[str] = set()

    # If config provides a page order, honour it
    if config and "pages" in config:
        for entry in config["pages"]:
            if isinstance(entry, str):
                stem = Path(entry).stem
                title_override = None
            else:
                stem = Path(entry["file"]).stem
                title_override = entry.get("title")

            if stem in md_files:
                md_path = md_files[stem]
                content = md_path.read_text(encoding="utf-8")
                title = title_override or extract_title(content, stem)
                pages.append(
                    {
                        "md_path": md_path,
                        "html_name": f"{stem}.html",
                        "title": title,
                        "slug": slugify(stem),
                    }
                )
                seen.add(stem)
            else:
                print(f"Warning: config references '{stem}.md' but file not found")

    # Append any remaining .md files not covered by config
    for stem, md_path in md_files.items():
        if stem in seen:
            continue
        content = md_path.read_text(encoding="utf-8")
        title = extract_title(content, stem)
        pages.append(
            {
                "md_path": md_path,
                "html_name": f"{stem}.html",
                "title": title,
                "slug": slugify(stem),
            }
        )

    return pages


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def build_nav_html(pages: list[dict], active_slug: str) -> str:
    """Generate the sidebar navigation HTML."""
    items: list[str] = []
    for page in pages:
        active = ' class="active"' if page["slug"] == active_slug else ""
        items.append(f'<li><a href="{page["html_name"]}"{active}>{page["title"]}</a></li>')
    return "\n            ".join(items)


def render_page(md_content: str, title: str, pages: list[dict],
                active_slug: str, project_title: str, lang: str) -> str:
    """Render a full HTML page with sidebar navigation."""
    nav_html = build_nav_html(pages, active_slug)
    body_html = simple_md_to_html(md_content)

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {project_title}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            line-height: 1.6; color: #24292f; margin: 0; display: flex; min-height: 100vh;
        }}
        nav {{
            width: 260px; min-width: 260px; padding: 20px; border-right: 1px solid #d0d7de;
            background: #f6f8fa; height: 100vh; position: sticky; top: 0; overflow-y: auto;
        }}
        nav h3 {{ margin-top: 0; color: #24292f; font-size: 1.1em; }}
        nav ul {{ list-style: none; padding: 0; margin: 0; }}
        nav li {{ margin: 4px 0; }}
        nav a {{ color: #0969da; text-decoration: none; display: block; padding: 4px 8px; border-radius: 6px; font-size: 0.9em; }}
        nav a:hover {{ background: #ddf4ff; }}
        nav a.active {{ background: #0969da; color: #fff; }}
        main {{ flex: 1; padding: 32px 48px; max-width: 900px; }}
        h1 {{ border-bottom: 1px solid #d0d7de; padding-bottom: 8px; }}
        h2 {{ border-bottom: 1px solid #d0d7de; padding-bottom: 6px; margin-top: 32px; }}
        code {{ background-color: #eff1f3; padding: 0.2em 0.4em; border-radius: 6px; font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 85%; }}
        pre {{ background-color: #f6f8fa; padding: 16px; border-radius: 6px; overflow: auto; line-height: 1.45; }}
        pre code {{ background: none; padding: 0; font-size: 85%; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        th, td {{ border: 1px solid #d0d7de; padding: 8px 16px; text-align: left; }}
        th {{ background-color: #f6f8fa; font-weight: 600; }}
        blockquote {{ border-left: 0.25em solid #d0d7de; color: #57606a; padding: 0 1em; margin: 16px 0; }}
        details {{ border: 1px solid #d0d7de; border-radius: 6px; padding: 12px; margin-bottom: 16px; }}
        summary {{ cursor: pointer; font-weight: 600; }}
        a {{ color: #0969da; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        img {{ max-width: 100%; height: auto; }}
        hr {{ border: none; border-top: 1px solid #d0d7de; margin: 24px 0; }}
        .mermaid {{ margin: 20px 0; text-align: center; }}
        @media (max-width: 768px) {{
            body {{ flex-direction: column; }}
            nav {{ width: 100%; height: auto; position: relative; border-right: none; border-bottom: 1px solid #d0d7de; }}
            nav ul {{ display: flex; flex-wrap: wrap; gap: 4px; }}
            main {{ padding: 20px; }}
        }}
    </style>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ startOnLoad: true }});
    </script>
</head>
<body>
    <nav>
        <h3>{project_title}</h3>
        <ul>
            {nav_html}
        </ul>
    </nav>
    <main>
        {body_html}
    </main>
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
        Directory containing .md source files.
    output_dir : str | None
        Directory for generated .html files. Defaults to *input_dir*.
    project_title : str
        Title shown in the sidebar header and <title> tag.
    lang : str
        HTML lang attribute (e.g. "en", "zh-CN").
    config : dict | None
        Optional config dict (from JSON) with page ordering / overrides.
    """
    output = Path(output_dir) if output_dir else Path(input_dir)
    output.mkdir(parents=True, exist_ok=True)

    pages = discover_pages(input_dir, config)
    if not pages:
        print(f"Error: no .md files found in '{input_dir}'")
        sys.exit(1)

    print(f"Building wiki: {len(pages)} page(s) from '{input_dir}' -> '{output}'")
    print(f"Project title: {project_title}")
    print()

    for page in pages:
        md_content = page["md_path"].read_text(encoding="utf-8")
        html_content = render_page(
            md_content=md_content,
            title=page["title"],
            pages=pages,
            active_slug=page["slug"],
            project_title=project_title,
            lang=lang,
        )

        html_path = output / page["html_name"]
        html_path.write_text(html_content, encoding="utf-8")
        print(f"  ✓ {page['html_name']:30s}  ({page['title']})")

    # Generate an index.html that redirects to the first page
    if pages:
        first_page = pages[0]["html_name"]
        index_path = output / "index.html"
        index_path.write_text(
            f'<!DOCTYPE html><html><head>'
            f'<meta http-equiv="refresh" content="0;url={first_page}">'
            f'</head><body><a href="{first_page}">Go to wiki</a></body></html>',
            encoding="utf-8",
        )
        print(f"  ✓ {'index.html':30s}  (redirect -> {first_page})")

    print(f"\nDone! Open {output / 'index.html'} in your browser.")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a directory of Markdown files into a static HTML wiki.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                  # ./wiki/*.md -> ./wiki/*.html
  %(prog)s -i docs/ -o site/                # docs/*.md   -> site/*.html
  %(prog)s -i wiki/ --title "My Project"    # custom project title
  %(prog)s --config wiki.json               # use config for page order
        """,
    )
    parser.add_argument(
        "-i", "--input",
        default="wiki",
        help="Input directory containing .md files (default: wiki)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output directory for .html files (default: same as input)",
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
        help="Path to a JSON config file for page ordering and metadata",
    )

    args = parser.parse_args()
    config = load_config(args.config)

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
