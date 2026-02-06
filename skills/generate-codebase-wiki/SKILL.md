---
name: generate-codebase-wiki
description: Generate a comprehensive, static HTML documentation wiki for the current codebase. Use when the user asks to "create a wiki", "document the codebase", or "generate documentation site".
---

# Generate Codebase Wiki

## Description
This skill guides the agent to create a structured, static HTML wiki for any GitHub repository or local codebase. The workflow is:
1. Analyze the repo and generate a wiki structure plan (XML).
2. Generate Markdown content for each planned page (with strict evidence-based citations).
3. Build a static HTML site with navigation using `build_wiki.py`.

## Workflow

### Step 1: Analyze & Plan Wiki Structure

Gather the following information from the repository:
- The complete file tree (use `ls -R` or file listing tools)
- The contents of `README.md` (or equivalent)
- Identify the repository owner and name

Then, use the **Wiki Structure Planning Prompt** below to generate a structured plan. The output is an XML document defining all pages, sections, relevant files, and relationships.

<details>
<summary><strong>Wiki Structure Planning Prompt (click to expand)</strong></summary>

Use the following prompt, replacing the `${...}` variables with actual values:

```
Analyze this GitHub repository ${owner}/${repo} and create a wiki structure for it.

1. The complete file tree of the project:
<file_tree>
${fileTree}
</file_tree>

2. The README file of the project:
<readme>
${readme}
</readme>

I want to create a wiki for this repository. Determine the most logical structure
for a wiki based on the repository's content.

IMPORTANT: The wiki content will be generated in english language.

When designing the wiki structure, include pages that would benefit from visual
diagrams, such as:
- Architecture overviews
- Data flow descriptions
- Component relationships
- Process workflows
- State machines
- Class hierarchies

Create a structured wiki with the following main sections (include only those
applicable to the project):
- Overview (general information about the project)
- System Architecture (how the system is designed)
- Core Features (key functionality)
- Data Management/Flow (database schema, data pipelines, state management)
- Frontend Components (UI elements, if applicable)
- Backend Systems (server-side components)
- Model Integration (AI model connections, if applicable)
- Deployment/Infrastructure (how to deploy, what the infrastructure looks like)
- Extensibility and Customization (plugins, theming, custom modules, hooks)

Each section should contain relevant pages. For example, the "Frontend Components"
section might include pages for "Home Page", "Dashboard", "Settings Panel", etc.

Return your analysis in the following XML format:

<wiki_structure>
  <title>[Overall title for the wiki]</title>
  <description>[Brief description of the repository]</description>
  <sections>
    <section id="section-1">
      <title>[Section title]</title>
      <pages>
        <page_ref>page-1</page_ref>
        <page_ref>page-2</page_ref>
      </pages>
      <subsections>
        <section_ref>section-2</section_ref>
      </subsections>
    </section>
    <!-- More sections as needed -->
  </sections>
  <pages>
    <page id="page-1">
      <title>[Page title]</title>
      <description>[Brief description of what this page will cover]</description>
      <importance>high|medium|low</importance>
      <relevant_files>
        <file_path>[Path to a relevant file]</file_path>
        <!-- More file paths as needed -->
      </relevant_files>
      <related_pages>
        <related>page-2</related>
        <!-- More related page IDs as needed -->
      </related_pages>
      <parent_section>section-1</parent_section>
    </page>
    <!-- More pages as needed -->
  </pages>
</wiki_structure>

IMPORTANT FORMATTING INSTRUCTIONS:
- Return ONLY the valid XML structure specified above
- DO NOT wrap the XML in markdown code blocks
- Ensure the XML is properly formatted and valid
- Start directly with <wiki_structure> and end with </wiki_structure>

IMPORTANT:
1. Create 8-12 pages that would make a comprehensive wiki for this repository
   (use 4-6 pages for smaller projects)
2. Each page should focus on a specific aspect of the codebase
3. The relevant_files should be actual files from the repository that would be
   used to generate that page
4. Return ONLY valid XML with the structure specified above
```

**Variable reference:**

| Variable      | Description           | Example                    |
| ------------- | --------------------- | -------------------------- |
| `${owner}`    | Repository owner      | `facebook`                 |
| `${repo}`     | Repository name       | `react`                    |
| `${fileTree}` | Full file tree output | Output of `find . -type f` |
| `${readme}`   | Contents of README.md | Raw markdown text          |

</details>

### Step 2: Generate Content (Iterative)

Parse the XML plan from Step 1. For each `<page>` entry:

1.  **Read the relevant source files** listed in `<relevant_files>`.
    -   **CRITICAL**: Each page **MUST** reference at least **5 source files**. If the plan lists fewer than 5, use search tools (`grep`, `codebase_search`) to find additional related files before writing.
2.  Generate a Markdown file using the **Page Content Generation Prompt** below.
3.  Save each file to the wiki output directory (e.g., `wiki/`). Use the page `id` as the filename (e.g., `page-1.md` or a slugified version of the title).

<details>
<summary><strong>Page Content Generation Prompt (click to expand)</strong></summary>

For each page, use the following prompt. Replace `${...}` variables with actual values from the XML plan and your file reads:

```
You are an expert technical writer and software architect.
Your task is to generate a comprehensive and accurate technical wiki page in
Markdown format about a specific feature, system, or module within a given
software project.

You will be given:
1. The "${page.title}" for the page you need to create.
2. A list of "${relevant_source_files}" from the project that you MUST use as
   the sole basis for the content. You have access to the full content of these
   files. You MUST use AT LEAST 5 relevant source files for comprehensive
   coverage - if fewer are provided, search for additional related files in the
   codebase.

CRITICAL STARTING INSTRUCTION:
The very first thing on the page MUST be a <details> block listing ALL the
source files you used to generate the content. There MUST be AT LEAST 5 source
files listed - if fewer were provided, you MUST find additional related files
to include.
Format it exactly like this:

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [path/to/file1.ext](${generateFileUrl("path/to/file1.ext")})
- [path/to/file2.ext](${generateFileUrl("path/to/file2.ext")})
...
<!-- Add additional relevant files if fewer than 5 were provided -->
</details>

Remember, do not provide any acknowledgements, disclaimers, apologies, or any
other preface before the <details> block. JUST START with the <details> block.

Immediately after the <details> block, the main title of the page should be a
H1 Markdown heading: # ${page.title}

Based ONLY on the content of the source files:

1.  **Introduction:** Start with a concise introduction (1-2 paragraphs)
    explaining the purpose, scope, and high-level overview of "${page.title}"
    within the context of the overall project. If relevant, and if information
    is available in the provided files, link to other potential wiki pages using
    the format [Link Text](#page-anchor-or-id).

2.  **Detailed Sections:** Break down "${page.title}" into logical sections
    using H2 (##) and H3 (###) Markdown headings. For each section:
    *   Explain the architecture, components, data flow, or logic relevant to
        the section's focus, as evidenced in the source files.
    *   Identify key functions, classes, data structures, API endpoints, or
        configuration elements pertinent to that section.

3.  **Mermaid Diagrams:**
    *   EXTENSIVELY use Mermaid diagrams (e.g., flowchart TD, sequenceDiagram,
        classDiagram, erDiagram, graph TD) to visually represent architectures,
        flows, relationships, and schemas found in the source files.
    *   Ensure diagrams are accurate and directly derived from information in
        the source files.
    *   Provide a brief explanation before or after each diagram to give context.
    *   CRITICAL: All diagrams MUST follow strict vertical orientation:
       - Use "graph TD" (top-down) directive for flow diagrams
       - NEVER use "graph LR" (left-right)
       - Maximum node width should be 3-4 words
       - For sequence diagrams:
         - Start with "sequenceDiagram" directive on its own line
         - Define ALL participants at the beginning using "participant" keyword
         - Optionally specify participant types: actor, boundary, control,
           entity, database, collections, queue
         - Use descriptive but concise participant names, or use aliases:
           "participant A as Alice"
         - Use the correct Mermaid arrow syntax (8 types available):
           - ->   solid line without arrow (rarely used)
           - -->  dotted line without arrow (rarely used)
           - ->>  solid line with arrowhead (most common for requests/calls)
           - -->> dotted line with arrowhead (most common for responses/returns)
           - ->x  solid line with X at end (failed/error message)
           - -->x dotted line with X at end (failed/error response)
           - -)   solid line with open arrow (async message, fire-and-forget)
           - --)  dotted line with open arrow (async response)
           - Examples: A->>B: Request, B-->>A: Response, A->xB: Error
         - Use +/- suffix for activation boxes:
           A->>+B: Start (activates B), B-->>-A: End (deactivates B)
         - Group related participants using "box": box GroupName ... end
         - Use structural elements for complex flows:
           - loop LoopText ... end (for iterations)
           - alt ConditionText ... else ... end (for conditionals)
           - opt OptionalText ... end (for optional flows)
           - par ParallelText ... and ... end (for parallel actions)
           - critical CriticalText ... option ... end (for critical regions)
           - break BreakText ... end (for breaking flows/exceptions)
         - Add notes: "Note over A,B: Description", "Note right of A: Detail"
         - Use autonumber directive to add sequence numbers to messages
         - NEVER use flowchart-style labels like A--|label|-->B.
           Always use a colon for labels: A->>B: My Label

4.  **Tables:**
    *   Use Markdown tables to summarize information such as:
        *   Key features or components and their descriptions.
        *   API endpoint parameters, types, and descriptions.
        *   Configuration options, their types, and default values.
        *   Data model fields, types, constraints, and descriptions.

5.  **Code Snippets (ENTIRELY OPTIONAL):**
    *   Include short, relevant code snippets directly from the source files to
        illustrate key implementation details, data structures, or configs.
    *   Ensure snippets are well-formatted within Markdown code blocks with
        appropriate language identifiers.

6.  **Source Citations (EXTREMELY IMPORTANT):**
    *   For EVERY piece of significant information, explanation, diagram, table
        entry, or code snippet, you MUST cite the specific source file(s) and
        relevant line numbers from which the information was derived.
    *   Place citations at the end of the paragraph, under the diagram/table,
        or after the code snippet.
    *   Use the exact format:
        Sources: [filename.ext:start_line-end_line]() for a range, or
        Sources: [filename.ext:line_number]() for a single line.
        Multiple files can be cited:
        Sources: [file1.ext:1-10](), [file2.ext:5](), [dir/file3.ext]()
    *   If an entire section is based on one or two files, cite them under the
        section heading in addition to more specific citations within.
    *   IMPORTANT: You MUST cite AT LEAST 5 different source files throughout
        the wiki page to ensure comprehensive coverage.

7.  **Technical Accuracy:** All information must be derived SOLELY from the
    source files. Do not infer, invent, or use external knowledge about similar
    systems or common practices unless directly supported by the provided code.
    If information is not present in the provided files, do not include it or
    explicitly state its absence if crucial to the topic.

8.  **Clarity and Conciseness:** Use clear, professional, and concise technical
    language suitable for other developers working on or learning about the
    project. Avoid unnecessary jargon, but use correct technical terms where
    appropriate.

9.  **Conclusion/Summary:** End with a brief summary paragraph if appropriate
    for "${page.title}", reiterating the key aspects covered and their
    significance within the project.

IMPORTANT: Generate the content in english language.

Remember:
- Ground every claim in the provided source files.
- Prioritize accuracy and direct representation of the code's functionality
  and structure.
- Structure the document logically for easy understanding by other developers.
```

**Variable reference:**

| Variable                   | Description                                         | Example                                  |
| -------------------------- | --------------------------------------------------- | ---------------------------------------- |
| `${page.title}`            | Page title from the XML plan `<title>` element      | `System Architecture`                    |
| `${relevant_source_files}` | File list from `<relevant_files>` in the XML plan   | List of file paths                       |
| `${generateFileUrl(path)}` | URL or relative path to the source file for linking | `https://github.com/owner/repo/blob/...` |

</details>

### Step 3: Build Static Site

Use the provided script `scripts/build_wiki.py` to convert Markdown files into a static HTML wiki.

**Basic usage:**
```bash
python build_wiki.py -i wiki/ -o wiki/ --title "Project Name Wiki"
```

**With config for page ordering** (recommended — use the plan from Step 1 to create this):
```bash
python build_wiki.py -i wiki/ --config wiki.json
```

Example `wiki.json` (generated from the XML plan):
```json
{
  "title": "My Project Wiki",
  "lang": "en",
  "pages": [
    "overview.md",
    {"file": "architecture.md", "title": "System Architecture"},
    "core_features.md",
    "data_flow.md"
  ]
}
```

**Key features of `build_wiki.py`:**
-   Auto-discovers all `.md` files in the input directory (no hardcoded lists).
-   Extracts page titles from `# Heading` in each Markdown file.
-   Generates a dynamic navigation sidebar with active-page highlighting.
-   Creates an `index.html` redirect to the first page.
-   Supports responsive layout (mobile-friendly).
-   Renders Mermaid diagrams via CDN.

**CLI options:**

| Flag           | Default         | Description                                 |
| -------------- | --------------- | ------------------------------------------- |
| `-i, --input`  | `wiki`          | Input directory containing `.md` files      |
| `-o, --output` | same as input   | Output directory for `.html` files          |
| `--title`      | `Codebase Wiki` | Project title (sidebar header & HTML title) |
| `--lang`       | `en`            | HTML `lang` attribute (`en`, `zh-CN`, etc.) |
| `--config`     | *(none)*        | JSON config for page ordering & metadata    |

---

## Rules & Constraints

1.  **Technical Accuracy**: Content must be derived **ONLY** from the provided source files. Do not hallucinate.
2.  **Language**: Generate wiki content in the language requested by the user (default: English). Adapt all section headers, descriptions, and body text to the chosen language.
3.  **No Fluff**: Professional, concise, developer-focused tone.
4.  **Minimum Coverage**: At least 5 source files per page; at least 5 citations per page.
5.  **Page Count**: 8-12 pages for comprehensive wikis; 4-6 for smaller projects.
6.  **Diagrams**: At least 1 Mermaid diagram per page where applicable (architecture, data flow, component relationships).
