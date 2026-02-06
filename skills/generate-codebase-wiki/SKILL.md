---
name: generate-codebase-wiki
description: Generate a comprehensive, static HTML documentation wiki for the current codebase. Use when the user asks to "create a wiki", "document the codebase", or "generate documentation site".
---

# Generate Codebase Wiki

## Description
This skill guides the agent to create a structured, static HTML wiki for the current codebase. It enforces strict evidence-based documentation, requiring at least 5 source files per page and precise citation formats.

## Workflow

1.  **Analyze & Plan**:
    *   Read `README.md` and the file tree.
    *   Create a plan for the wiki structure based on the **Required Sections** below.
    *   Identify the key source files for each section.

2.  **Generate Content (Iterative)**:
    *   For each page in the plan, generate a Markdown file.
    *   **CRITICAL**: You **MUST** use at least **5 relevant source files** for each page. If you have fewer than 5, use `grep` or `codebase_search` to find more related files before generating content.
    *   Follow the **Page Content Template** strictly.

3.  **Build Static Site**:
    *   Use the provided script `scripts/build_wiki.py` to convert Markdown files to static HTML.
    *   **IMPORTANT**: You must update the `files` list in `scripts/build_wiki.py` (or a copy of it) to match the actual pages you generated.
    *   Run the script to generate the HTML files.
    *   The site must have a navigation sidebar linking to all pages.
    *   Ensure all internal links (e.g., `[Link](#anchor)`) work in the HTML version.

## Required Sections (Wiki Structure)

Create pages for the following sections (adapt as applicable to the project):

1.  **概览 (Overview)**: General project information.
2.  **系统架构 (System Architecture)**: High-level design.
3.  **核心功能 (Core Features)**: Key functionalities.
4.  **数据管理/流 (Data Management/Flow)**: Database schemas, pipelines, state management.
5.  **前端组件 (Frontend Components)**: UI elements, pages (if applicable).
6.  **后端系统 (Backend Systems)**: Server-side components, APIs.
7.  **模型集成 (Model Integration)**: AI model connections (if applicable).
8.  **部署/基础设施 (Deployment/Infrastructure)**: Deployment process, infra setup.
9.  **可扩展性与自定义 (Scalability & Customization)**: Plugins, hooks, themes (if applicable).

## Page Content Template (Strict)

Every wiki page **MUST** follow this exact format:

### 1. Source Files Header
The page **MUST** start with this exact HTML block. Do not add any text before it.

```html
<details>
<summary>Relevant source files</summary>

以下文件被用作生成此 Wiki 页面的上下文：

- [path/to/file1.ext](path/to/file1.ext)
- [path/to/file2.ext](path/to/file2.ext)
- [path/to/file3.ext](path/to/file3.ext)
- [path/to/file4.ext](path/to/file4.ext)
- [path/to/file5.ext](path/to/file5.ext)
<!-- Must list at least 5 files. If fewer, find more. -->
</details>
```

### 2. Title
`# ${page.title}`

### 3. Content Body
**1. 简介 (Introduction):**
*   1-2 paragraphs explaining the purpose and scope of this section.
*   Use `[Link Text](#anchor)` for cross-references.

**2. 详细章节 (Detailed Sections):**
*   Use H2 (`##`) and H3 (`###`) headers.
*   Explain architecture, components, data flow, or logic based **ONLY** on the source files.
*   Identify key functions, classes, API endpoints, or configuration elements.

**3. Mermaid 图表 (Mermaid Diagrams):**
*   Use diagrams extensively (flowchart, sequence, class, ER, etc.).
*   **STRICT ORIENTATION RULES**:
    *   Flowcharts: MUST use `graph TD` (Top-Down). **NEVER** use `graph LR`.
    *   Max node width: 3-4 words.
*   **Sequence Diagram Rules**:
    *   Start with `sequenceDiagram`.
    *   Define participants: `participant A as Alice`.
    *   Use correct arrows: `->>` (request), `-->>` (response), `->x` (error), `-)` (async).
    *   Use `opt`, `alt`, `loop`, `par` for control flow.
    *   **NEVER** use flowchart-style labels (e.g., `A--|label|-->B`). Use colons: `A->>B: Label`.

**4. 表格 (Tables):**
*   Summarize key features, API parameters, config options, or data fields.

**5. 代码片段 (Code Snippets) [Optional]:**
*   Short, relevant snippets from source files.

### 4. Citations (CRITICAL)
Every claim, diagram, or table entry **MUST** cite its source.
*   **Format**: `Sources: [filename.ext:start_line-end_line]()` or `Sources: [filename.ext:line_number]()`.
*   **Placement**: End of paragraphs, below diagrams/tables, or after code snippets.
*   **Requirement**: You must cite at least 5 different files across the page.

### 5. Conclusion
**结论/总结 (Conclusion):**
*   Brief summary of key points.

## Rules & Constraints
1.  **Technical Accuracy**: Content must be derived **ONLY** from the provided source files. Do not hallucinate.
2.  **Language**: Use the language requested by the user for the content (default to the codebase language if unspecified). The headers in the template above are in Chinese as per the original request; preserve them unless instructed otherwise.
3.  **No Fluff**: Professional, concise, developer-focused tone.
