---
name: generate-codebase-wiki
description: Generate a comprehensive, static HTML documentation wiki for the current codebase. Use when the user asks to "create a wiki", "document the codebase", or "generate documentation site".
---

# Generate Codebase Wiki

## Description
This skill guides the agent to create a structured, static HTML wiki for any GitHub repository or local codebase. It adapts to both small and large repositories, producing multi-level hierarchical documentation for complex projects.

**IMPORTANT — Bundled Script:**
This skill ships with a ready-to-use build script at:
```
<SKILL_DIR>/scripts/build_wiki.py
```
Where `<SKILL_DIR>` is the directory containing this `SKILL.md` file.
**You MUST use this bundled script. Do NOT re-create or re-generate `build_wiki.py`.**
Before running the script, resolve the absolute path. For example, if this SKILL.md is at
`/path/to/skills/generate-codebase-wiki/SKILL.md`, then the script is at
`/path/to/skills/generate-codebase-wiki/scripts/build_wiki.py`.

The workflow is:
1. Assess the repository size and complexity.
2. Analyze the repo and generate a wiki structure plan (XML) scaled to the repo.
3. Generate Markdown content for each planned page (with strict evidence-based citations).
4. Build a static HTML site with hierarchical navigation using the **bundled** `build_wiki.py`.

## Workflow

### Step 1: Assess Repository Size & Complexity

Before planning the wiki structure, assess the repository to determine its scale. This drives how many pages, sections, and levels of depth the wiki should have.

**Gather these data points:**
- Total number of source files (excluding vendored/generated code)
- Number of distinct top-level directories (modules / packages / services)
- Presence of multiple services, microservices, or independently deployable components
- Whether the project has API definitions (REST, gRPC, GraphQL, etc.)
- Whether the project interacts with external services or has inter-service communication

**Classification:**

| Category   | Source Files | Top-level Modules | Wiki Pages | Section Depth |
| ---------- | ------------ | ----------------- | ---------- | ------------- |
| **Small**  | < 50         | 1-3               | 4-8        | 1 level       |
| **Medium** | 50-300       | 3-8               | 8-16       | 2 levels      |
| **Large**  | 300+         | 8+                | 16-40+     | 2-3 levels    |

For **large repositories**, the wiki MUST include dedicated sections for:
- **System Architecture** — overall architecture, design patterns, component topology
- **Module Deep Dives** — one page per major module/package with internal design details
- **External Interfaces** — all APIs, SDKs, CLI commands, or protocols exposed to consumers
- **Service Relationships** — how this service connects to databases, message queues, peer services, and third-party APIs
- **Data Models & Storage** — schemas, migrations, data flow through the system
- **Deployment & Infrastructure** — containerization, orchestration, CI/CD, environment configuration

### Step 2: Plan Wiki Structure

Gather the following information from the repository:
- The complete file tree (use `ls -R` or file listing tools; for large repos, limit depth to 3-4 levels)
- The contents of `README.md` (or equivalent)
- Identify the repository owner and name
- For large repos, also scan: `Makefile`, `docker-compose.yml`, `*.proto`, `openapi.yaml`, `swagger.json`, CI config files, and entry points

Then, use the **Wiki Structure Planning Prompt** below to generate a structured plan. The output is an XML document defining all sections, pages, their hierarchy, relevant files, and relationships.

<details>
<summary><strong>Wiki Structure Planning Prompt (click to expand)</strong></summary>

Use the following prompt, replacing the `${...}` variables with actual values:

```
Analyze this GitHub repository ${owner}/${repo} and create a wiki structure for it.

Repository complexity classification: ${repoSize} (small / medium / large)

1. The complete file tree of the project:
<file_tree>
${fileTree}
</file_tree>

2. The README file of the project:
<readme>
${readme}
</readme>

I want to create a multi-level wiki for this repository. The wiki must scale
to the repository's complexity:
- Small repos (< 50 files): 4-8 pages, 1 level of sections
- Medium repos (50-300 files): 8-16 pages, 2 levels of sections
- Large repos (300+ files): 16-40+ pages, 2-3 levels of sections with
  deep-dive sub-pages

IMPORTANT: The wiki content will be generated in english language.

When designing the wiki structure, ALWAYS include pages that would benefit
from visual diagrams, such as:
- Architecture overviews (system-level and module-level)
- Data flow descriptions (request lifecycle, event propagation)
- Component relationships and dependency graphs
- Process workflows and state machines
- API request/response flows
- Deployment topology and infrastructure diagrams

FOR LARGE REPOSITORIES, you MUST include the following top-level sections
(include all that are applicable):

1. **Project Overview**
   - General information, goals, tech stack
   - Getting started / quick start guide

2. **System Architecture**
   - High-level architecture overview (components, layers, patterns)
   - Design decisions and trade-offs
   - Component topology diagram

3. **Module Deep Dives** (one sub-page per major module/package)
   - Internal design and responsibility
   - Key classes/functions and their interactions
   - Extension points and hooks

4. **External Interfaces**
   - REST/gRPC/GraphQL API reference
   - SDK / client library documentation
   - CLI commands and options
   - Event/message schemas (if applicable)

5. **Service Relationships & Integration**
   - Dependency map (upstream/downstream services)
   - Database connections and data stores
   - Message queue / event bus integrations
   - Third-party API integrations
   - Authentication and authorization flow across services

6. **Data Models & Storage**
   - Database schema and entity relationships
   - Data flow through the system
   - Caching strategies
   - Migration approach

7. **Core Features** (group by domain area)
   - Key functionality with implementation details
   - Business logic and rules

8. **Configuration & Environment**
   - Configuration options, environment variables
   - Feature flags, runtime settings

9. **Deployment & Infrastructure**
   - Build process and CI/CD pipeline
   - Container/orchestration setup
   - Monitoring and observability
   - Scaling and performance considerations

10. **Development Guide**
    - Local development setup
    - Testing strategy and test structure
    - Contributing guidelines

FOR SMALL/MEDIUM REPOSITORIES, include only the applicable sections and merge
related topics. Typical structure:
- Overview
- Architecture
- Core Features (1-3 pages)
- API / Interfaces (if applicable)
- Data Management
- Configuration & Deployment

Return your analysis in the following XML format:

<wiki_structure>
  <title>[Overall title for the wiki]</title>
  <description>[Brief description of the repository]</description>
  <repo_size>small|medium|large</repo_size>
  <sections>
    <section id="section-1">
      <title>[Section title]</title>
      <pages>
        <page_ref>page-1</page_ref>
        <page_ref>page-2</page_ref>
      </pages>
      <subsections>
        <section id="section-1-1">
          <title>[Subsection title]</title>
          <pages>
            <page_ref>page-3</page_ref>
            <page_ref>page-4</page_ref>
          </pages>
        </section>
        <!-- More subsections as needed -->
      </subsections>
    </section>
    <!-- More top-level sections as needed -->
  </sections>
  <pages>
    <page id="page-1">
      <title>[Page title]</title>
      <description>[Brief description of what this page will cover]</description>
      <importance>high|medium|low</importance>
      <page_type>overview|architecture|deep-dive|api-reference|integration|data-model|guide</page_type>
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
- Subsections are nested WITHIN their parent section element
- Every page MUST have a parent_section that matches a section id

IMPORTANT:
1. Scale the number of pages to the repository complexity
   (small: 4-8, medium: 8-16, large: 16-40+)
2. Each page should focus on a specific aspect of the codebase
3. The relevant_files should be actual files from the repository that would be
   used to generate that page
4. For large repos, each module/package should get its own deep-dive page
5. API and interface pages must list all endpoint/method definition files
6. Return ONLY valid XML with the structure specified above
```

**Variable reference:**

| Variable      | Description                                           | Example                    |
| ------------- | ----------------------------------------------------- | -------------------------- |
| `${owner}`    | Repository owner                                      | `facebook`                 |
| `${repo}`     | Repository name                                       | `react`                    |
| `${repoSize}` | Assessed size from Step 1                             | `large`                    |
| `${fileTree}` | Full file tree output (depth-limited for large repos) | Output of `find . -type f` |
| `${readme}`   | Contents of README.md                                 | Raw markdown text          |

</details>

### Step 3: Generate Content (Iterative)

Parse the XML plan from Step 2. For each `<page>` entry:

1.  **Read the relevant source files** listed in `<relevant_files>`.
    -   **CRITICAL**: Each page **MUST** reference at least **5 source files**. If the plan lists fewer than 5, use search tools (`grep`, `codebase_search`) to find additional related files before writing.
    -   For **API reference pages**, read ALL endpoint/handler definition files.
    -   For **architecture pages**, read entry points, main config files, and dependency declarations.
    -   For **service relationship pages**, read client/SDK code, connection configs, and integration adapters.
2.  Generate a Markdown file using the appropriate **Page Content Generation Prompt** below (choose based on `page_type`).
3.  Save each file to the wiki output directory. Organize files into subdirectories matching the section hierarchy:
    ```
    wiki/
    ├── overview.md
    ├── architecture/
    │   ├── system-overview.md
    │   └── design-decisions.md
    ├── modules/
    │   ├── auth-module.md
    │   ├── payment-module.md
    │   └── notification-module.md
    ├── api/
    │   ├── rest-api.md
    │   └── grpc-api.md
    └── deployment/
        └── infrastructure.md
    ```
    For small repos, a flat structure is acceptable.

<details>
<summary><strong>Page Content Generation Prompt — General (click to expand)</strong></summary>

For each page, use the following prompt. Replace `${...}` variables with actual values from the XML plan and your file reads:

```
You are an expert technical writer and software architect.
Your task is to generate a comprehensive and accurate technical wiki page in
Markdown format about a specific feature, system, or module within a given
software project.

You will be given:
1. The "${page.title}" for the page you need to create.
2. The page type: "${page.page_type}" (overview|architecture|deep-dive|
   api-reference|integration|data-model|guide)
3. A list of "${relevant_source_files}" from the project that you MUST use as
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
    within the context of the overall project. If relevant, link to related wiki
    pages using the format [Link Text](../section/page-name.md).

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
         - Use the correct Mermaid arrow syntax:
           - ->>  solid line with arrowhead (requests/calls)
           - -->> dotted line with arrowhead (responses/returns)
           - ->x  solid line with X (failed/error)
           - -)   solid line with open arrow (async, fire-and-forget)
         - Use +/- for activation: A->>+B: Start, B-->>-A: End
         - Group with "box": box GroupName ... end
         - Structural elements: loop, alt/else, opt, par/and, critical/option, break

4.  **Tables:**
    *   Use Markdown tables to summarize information such as:
        *   Key features or components and their descriptions.
        *   API endpoint parameters, types, and descriptions.
        *   Configuration options, their types, and default values.
        *   Data model fields, types, constraints, and descriptions.

5.  **Code Snippets (ENTIRELY OPTIONAL):**
    *   Include short, relevant code snippets directly from the source files to
        illustrate key implementation details, data structures, or configs.

6.  **Source Citations (EXTREMELY IMPORTANT):**
    *   For EVERY piece of significant information, you MUST cite the specific
        source file(s) and relevant line numbers.
    *   Use the exact format:
        Sources: [filename.ext:start_line-end_line]() for a range, or
        Sources: [filename.ext:line_number]() for a single line.
        Multiple files can be cited:
        Sources: [file1.ext:1-10](), [file2.ext:5](), [dir/file3.ext]()
    *   You MUST cite AT LEAST 5 different source files throughout the page.

7.  **Technical Accuracy:** All information must be derived SOLELY from the
    source files. Do not infer, invent, or use external knowledge.

8.  **Clarity and Conciseness:** Use clear, professional, concise technical
    language suitable for other developers.

9.  **Cross-references:** When mentioning concepts covered in other wiki pages,
    add cross-reference links: [Related Topic](../section/page-name.md).

IMPORTANT: Generate the content in english language.

Remember:
- Ground every claim in the provided source files.
- Prioritize accuracy and direct representation of the code.
- Structure the document logically for easy understanding.
```

</details>

<details>
<summary><strong>Page Content Generation Prompt — Architecture Overview (click to expand)</strong></summary>

Use this specialized prompt for pages with `page_type="architecture"`:

```
You are an expert software architect and technical writer.
Your task is to generate a comprehensive ARCHITECTURE OVERVIEW wiki page for
the project "${page.title}".

Source files: ${relevant_source_files}

CRITICAL STARTING INSTRUCTION:
Start with the <details> block listing all source files (minimum 5), then
# ${page.title}

This is an ARCHITECTURE page. It MUST include:

1.  **Architecture Overview** (2-3 paragraphs)
    - What the system does at a high level
    - Key architectural patterns used (MVC, microservices, event-driven, etc.)
    - Technology stack summary

2.  **System Component Diagram** (REQUIRED Mermaid diagram)
    - Show ALL major components/services/modules
    - Show data flow directions between components
    - Use graph TD (top-down) orientation
    - Include external dependencies (databases, caches, queues, third-party APIs)

3.  **Layer Architecture** (if applicable)
    - Describe each layer (presentation, business logic, data access, etc.)
    - Show dependencies between layers
    - Include a Mermaid diagram showing the layer stack

4.  **Request Lifecycle** (REQUIRED sequence diagram)
    - Trace a typical request from client to response
    - Show all components touched along the way
    - Include error handling paths

5.  **Key Design Decisions**
    - Document significant architectural choices found in the codebase
    - For each: what was chosen, and what trade-offs it implies

6.  **Module/Package Organization**
    - Table listing all major modules, their responsibility, and key entry points
    - Dependency graph between modules (Mermaid diagram)

7.  **Cross-cutting Concerns**
    - How logging, error handling, authentication, and configuration are handled
    - Where these concerns are implemented

Source citations required for every claim. Minimum 5 source files cited.
Generate in english language.
```

</details>

<details>
<summary><strong>Page Content Generation Prompt — API / External Interfaces (click to expand)</strong></summary>

Use this specialized prompt for pages with `page_type="api-reference"`:

```
You are an expert API documentation writer.
Your task is to generate a comprehensive API REFERENCE wiki page for
"${page.title}".

Source files: ${relevant_source_files}

CRITICAL STARTING INSTRUCTION:
Start with the <details> block listing all source files (minimum 5), then
# ${page.title}

This is an API REFERENCE page. It MUST include:

1.  **API Overview**
    - What this API provides
    - Base URL / connection details (if found in code)
    - Authentication/authorization requirements
    - Common request/response patterns

2.  **Endpoint / Method Summary Table** (REQUIRED)
    | Method | Path / Name | Description | Auth Required |
    | ------ | ----------- | ----------- | ------------- |
    | GET    | /api/users  | List users  | Yes           |

3.  **Detailed Endpoint Documentation** (for each endpoint/method):
    - HTTP method + path (or RPC method name)
    - Request parameters (path, query, body) with types and constraints
    - Request body schema (if applicable)
    - Response schema with field descriptions
    - Error responses and status codes
    - Example request/response (from source code, tests, or comments)

4.  **Data Transfer Objects / Schemas**
    - Document all request/response DTOs
    - Include field types, validation rules, and defaults
    - Use tables or code blocks for schema definitions

5.  **API Flow Diagrams** (REQUIRED for complex flows)
    - Sequence diagrams for multi-step API interactions
    - Authentication flow diagram
    - Webhook/callback flow (if applicable)

6.  **Error Handling**
    - Standard error response format
    - Error code reference table
    - Rate limiting details (if found in code)

Source citations required for every endpoint. Minimum 5 source files cited.
Generate in english language.
```

</details>

<details>
<summary><strong>Page Content Generation Prompt — Service Relationships (click to expand)</strong></summary>

Use this specialized prompt for pages with `page_type="integration"`:

```
You are an expert systems integration architect.
Your task is to generate a comprehensive SERVICE RELATIONSHIPS wiki page for
"${page.title}".

Source files: ${relevant_source_files}

CRITICAL STARTING INSTRUCTION:
Start with the <details> block listing all source files (minimum 5), then
# ${page.title}

This is a SERVICE RELATIONSHIPS page. It MUST include:

1.  **Integration Overview**
    - What external systems this service connects to
    - Overall integration architecture pattern (sync/async, event-driven, etc.)

2.  **Service Dependency Map** (REQUIRED Mermaid diagram)
    - Show this service at the center
    - Show ALL upstream services (services this depends on)
    - Show ALL downstream services (services that depend on this)
    - Show databases, caches, message queues, and external APIs
    - Use directional arrows showing data/request flow

3.  **For EACH Integration**, document:
    - **Service name** and purpose
    - **Communication protocol** (REST, gRPC, message queue, database, etc.)
    - **Connection configuration** (how it's configured, environment variables)
    - **Data exchanged** (request/response schemas, event payloads)
    - **Error handling and resilience** (retries, circuit breakers, fallbacks)
    - **Sequence diagram** showing the interaction flow

4.  **Database & Data Store Connections**
    - List all databases/stores with connection details
    - ORM/client library used
    - Connection pooling configuration
    - Schema/migration management

5.  **Message Queue / Event Bus**
    - Topics/queues produced to and consumed from
    - Message schemas
    - Consumer group configuration
    - Dead letter queue handling

6.  **Third-party API Integrations**
    - Each external API called
    - Authentication method
    - Rate limits and quotas
    - SDK or client library used

7.  **Health Checks & Monitoring**
    - How integration health is monitored
    - Circuit breaker states
    - Alerting configuration

Source citations required for every integration. Minimum 5 source files cited.
Generate in english language.
```

</details>

**Variable reference (all prompts):**

| Variable                   | Description                                         | Example                                  |
| -------------------------- | --------------------------------------------------- | ---------------------------------------- |
| `${page.title}`            | Page title from the XML plan `<title>` element      | `System Architecture`                    |
| `${page.page_type}`        | Page type from the XML plan `<page_type>` element   | `architecture`                           |
| `${relevant_source_files}` | File list from `<relevant_files>` in the XML plan   | List of file paths                       |
| `${generateFileUrl(path)}` | URL or relative path to the source file for linking | `https://github.com/owner/repo/blob/...` |

### Step 4: Build Static Site

Use the **bundled** script to convert Markdown files into a static HTML wiki with hierarchical navigation.

**CRITICAL: Do NOT write your own `build_wiki.py`. Use the one bundled with this skill.**

First, resolve the script path. If this SKILL.md is located at:
`/path/to/skills/generate-codebase-wiki/SKILL.md`
then the script is at:
`/path/to/skills/generate-codebase-wiki/scripts/build_wiki.py`

**Basic usage (small repos, flat structure):**
```bash
python /path/to/skills/generate-codebase-wiki/scripts/build_wiki.py -i wiki/ -o wiki/ --title "Project Name Wiki"
```

**With config for hierarchical structure (recommended for medium/large repos):**
```bash
python /path/to/skills/generate-codebase-wiki/scripts/build_wiki.py -i wiki/ --config wiki.json
```

Example `wiki.json` for a **small repo** (flat structure):
```json
{
  "title": "My Small Project Wiki",
  "lang": "en",
  "pages": [
    "overview.md",
    {"file": "architecture.md", "title": "System Architecture"},
    "core_features.md",
    "data_flow.md"
  ]
}
```

Example `wiki.json` for a **large repo** (hierarchical structure):
```json
{
  "title": "My Platform Wiki",
  "lang": "en",
  "sections": [
    {
      "title": "Project Overview",
      "pages": ["overview.md", "getting-started.md"]
    },
    {
      "title": "System Architecture",
      "pages": ["architecture/system-overview.md", "architecture/design-decisions.md"]
    },
    {
      "title": "Module Deep Dives",
      "pages": [
        "modules/auth-module.md",
        "modules/payment-module.md",
        "modules/notification-module.md"
      ],
      "subsections": [
        {
          "title": "Auth Internals",
          "pages": ["modules/auth/oauth-flow.md", "modules/auth/rbac.md"]
        }
      ]
    },
    {
      "title": "External Interfaces",
      "pages": ["api/rest-api.md", "api/grpc-api.md", "api/webhooks.md"]
    },
    {
      "title": "Service Relationships",
      "pages": ["integration/service-map.md", "integration/database.md", "integration/message-queue.md"]
    },
    {
      "title": "Deployment",
      "pages": ["deployment/infrastructure.md", "deployment/ci-cd.md"]
    }
  ]
}
```

**Key features of `build_wiki.py`:**
-   Auto-discovers all `.md` files in the input directory **and subdirectories** (recursive).
-   Supports **hierarchical navigation** with collapsible sections in the sidebar.
-   Generates **breadcrumb navigation** for nested pages.
-   Includes **client-side full-text search** across all pages.
-   Generates **per-page table of contents** from headings.
-   Extracts page titles from `# Heading` in each Markdown file.
-   Generates a dynamic navigation sidebar with active-page highlighting.
-   Creates an `index.html` redirect to the first page.
-   Supports responsive layout (mobile-friendly).
-   Renders Mermaid diagrams via CDN.

**CLI options:**

| Flag           | Default         | Description                                  |
| -------------- | --------------- | -------------------------------------------- |
| `-i, --input`  | `wiki`          | Input directory containing `.md` files       |
| `-o, --output` | same as input   | Output directory for `.html` files           |
| `--title`      | `Codebase Wiki` | Project title (sidebar header & HTML title)  |
| `--lang`       | `en`            | HTML `lang` attribute (`en`, `zh-CN`, etc.)  |
| `--config`     | *(none)*        | JSON config for section hierarchy & metadata |

---

## Rules & Constraints

1.  **Technical Accuracy**: Content must be derived **ONLY** from the provided source files. Do not hallucinate.
2.  **Language**: Generate wiki content in the language requested by the user (default: English). Adapt all section headers, descriptions, and body text to the chosen language.
3.  **No Fluff**: Professional, concise, developer-focused tone.
4.  **Minimum Coverage**: At least 5 source files per page; at least 5 citations per page.
5.  **Page Count**: Scale to repo size — small: 4-8, medium: 8-16, large: 16-40+.
6.  **Diagrams**: At least 1 Mermaid diagram per page where applicable (architecture, data flow, component relationships). Architecture pages MUST have at least 2 diagrams.
7.  **Hierarchy**: Large repos MUST use multi-level sections. Group related pages under common sections.
8.  **Cross-references**: Pages MUST link to related pages when mentioning concepts covered elsewhere in the wiki.
9.  **API Documentation**: All public APIs/interfaces MUST be documented with endpoint tables, parameter types, and response schemas.
10. **Service Relationships**: For multi-service projects, MUST include a service dependency map with communication protocols and data flow.
