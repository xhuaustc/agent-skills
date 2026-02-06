import os
import re

def simple_md_to_html(md_content):
    html = md_content
    
    # Escape HTML characters
    html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # Restore <details> and <summary> blocks (specific to this wiki)
    html = html.replace("&lt;details&gt;", "<details>").replace("&lt;/details&gt;", "</details>")
    html = html.replace("&lt;summary&gt;", "<summary>").replace("&lt;/summary&gt;", "</summary>")
    
    # Headers
    html = re.sub(r'^# (.*$)', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*$)', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*$)', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    
    # Bold
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    
    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)
    
    # Unordered Lists
    html = re.sub(r'^\* (.*$)', r'<ul><li>\1</li></ul>', html, flags=re.MULTILINE)
    html = re.sub(r'^- (.*$)', r'<ul><li>\1</li></ul>', html, flags=re.MULTILINE)
    # Fix nested lists (naive approach)
    html = html.replace("</ul>\n<ul>", "")
    
    # Code Blocks (fenced)
    # Handle mermaid specifically first to avoid escaping issues if we want them rendered
    # But for now, let's just make them code blocks with class mermaid
    
    def code_block_replacer(match):
        lang = match.group(1) or ""
        code = match.group(2)
        if lang == "mermaid":
            return f'<div class="mermaid">{code}</div>'
        return f'<pre><code class="language-{lang}">{code}</code></pre>'
        
    html = re.sub(r'```(\w*)\n([\s\S]*?)```', code_block_replacer, html)
    
    # Inline Code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # Paragraphs (naive: double newline is new paragraph)
    # html = re.sub(r'\n\n([^<].*?)\n', r'<p>\1</p>', html)
    
    # Tables (very basic support)
    def table_replacer(match):
        rows = match.group(0).strip().split('\n')
        table_html = '<table>'
        for i, row in enumerate(rows):
            cols = [c.strip() for c in row.strip('|').split('|')]
            if i == 1 and set(row) <= set('|:- '): continue # Skip separator line
            
            tag = 'th' if i == 0 else 'td'
            table_html += '<tr>' + ''.join(f'<{tag}>{col}</{tag}>' for col in cols) + '</tr>'
        table_html += '</table>'
        return table_html

    html = re.sub(r'\|.*\|\n\|[-:| ]+\|\n(\|.*\|\n)+', table_replacer, html)

    # Convert newlines to <br> for text not in tags (simplified)
    # This is tricky without a proper parser, so we'll skip for now and rely on block elements
    
    return html

def convert_md_to_html_page(md_content, title):
    # Basic HTML template
    html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Codebase Wiki</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; display: flex; }}
        nav {{ width: 250px; padding: 20px; border-right: 1px solid #eee; height: 100vh; position: sticky; top: 0; overflow-y: auto; }}
        main {{ flex: 1; padding: 40px; max-width: 800px; }}
        h1, h2, h3 {{ color: #24292e; }}
        code {{ background-color: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace; }}
        pre {{ background-color: #f6f8fa; padding: 16px; border-radius: 6px; overflow: auto; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        th, td {{ border: 1px solid #dfe2e5; padding: 6px 13px; }}
        th {{ background-color: #f6f8fa; }}
        blockquote {{ border-left: 0.25em solid #dfe2e5; color: #6a737d; padding: 0 1em; margin: 0; }}
        details {{ border: 1px solid #e1e4e8; border-radius: 6px; padding: 8px; margin-bottom: 16px; }}
        summary {{ cursor: pointer; font-weight: bold; }}
        a {{ color: #0366d6; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .mermaid {{ margin: 20px 0; text-align: center; }}
    </style>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ startOnLoad: true }});
    </script>
</head>
<body>
    <nav>
        <h3>Wiki Navigation</h3>
        <ul>
            <li><a href="overview.html">概览 (Overview)</a></li>
            <li><a href="core_features.html">核心功能 (Core Features)</a></li>
            <li><a href="architecture.html">系统架构 (Architecture)</a></li>
            <li><a href="history.html">开发历史 (History)</a></li>
        </ul>
    </nav>
    <main>
        {simple_md_to_html(md_content)}
    </main>
</body>
</html>
    """
    return html_template

def build_wiki():
    wiki_dir = 'wiki'
    files = [
        ('overview.md', '概览'),
        ('core_features.md', '核心功能'),
        ('architecture.md', '系统架构'),
        ('history.md', '开发历史')
    ]
    
    for filename, title in files:
        md_path = os.path.join(wiki_dir, filename)
        html_path = os.path.join(wiki_dir, filename.replace('.md', '.html'))
        
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            html_content = convert_md_to_html_page(md_content, title)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"Generated {html_path}")
        else:
            print(f"Warning: {md_path} not found")

if __name__ == "__main__":
    build_wiki()
