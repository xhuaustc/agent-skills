# AI Agent Skills

This repository contains a collection of skills designed to enhance the capabilities of AI coding assistants (specifically for Cursor). Each skill provides specialized knowledge and workflows for specific tasks.

## Directory Structure

```text
.
├── skills/                 # Source of truth for all skills
│   ├── generate-codebase-wiki/
│   │   ├── SKILL.md       # Skill definition
│   │   └── scripts/       # Helper scripts
│   └── send-notification/
│       └── SKILL.md
├── .cursor/                # Cursor configuration
│   └── skills/            # Active skills in Cursor context
└── wiki/                   # Generated documentation (example output)
```

## Available Skills

### 1. Generate Codebase Wiki
**Location:** `skills/generate-codebase-wiki/`

A comprehensive skill to generate a static HTML documentation wiki for the current codebase. It enforces strict evidence-based documentation.

-   **Features:**
    -   Generates structured documentation (Overview, Architecture, Core Features, etc.).
    -   Requires source file citations for accuracy.
    -   Includes a Python script (`scripts/build_wiki.py`) to convert Markdown to a static HTML site.
    -   Supports Mermaid diagrams for visualization.

### 2. Send Notification
**Location:** `skills/send-notification/`

A utility skill to generate professional company team announcement emails.

-   **Features:**
    -   Structured email generation based on "Who", "What", and "Action Required".
    -   Professional corporate tone.
    -   Standardized formatting for clear communication.

## Usage

To use a skill, the AI agent reads the `SKILL.md` file to understand the specific workflow, rules, and templates associated with that capability.

## Adding a New Skill

1.  Create a new directory in `skills/<skill-name>`.
2.  Add a `SKILL.md` file with the skill definition, including:
    -   Frontmatter (name, description).
    -   Detailed instructions/workflow.
    -   Templates and examples.
3.  Add any necessary helper scripts or resources in the skill directory.
