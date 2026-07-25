---
name: mermaid
description: "Create Mermaid diagrams compatible with Obsidian, GitHub, and Notion. Use when creating or fixing diagrams in markdown files. Ensures cross-platform compatibility and avoids common rendering bugs."
argument-hint: <diagram-type> <description> | fix <file>
---

# Mermaid Diagram Generator

Generate Mermaid diagrams that render correctly across Obsidian, GitHub, and Notion.

## How to Use

When the user asks to create a Mermaid diagram, or when you are writing Mermaid blocks in any markdown file, follow every rule below. When the user says `/mermaid fix <file>`, scan the file for broken Mermaid blocks and fix them.

---

## CRITICAL RULES — Always Follow

### 1. Node Labels

- **ALWAYS quote labels**: `A["My Label"]` — never `A[My Label]` if it has spaces or special chars
- **NEVER use `<br/>` or `<br>` in labels** — Obsidian interprets these as "Unsupported markdown: list"
- **NEVER use markdown syntax in labels** (no `**bold**`, `- list items`, `* bullets`)
- **Keep labels short** — one line, under 40 characters. Put details in a markdown table next to the diagram
- **Use ASCII-only for node IDs**: `A`, `B1`, `nodeX` — never `café`, `ação`, `résumé`
- **Accented characters are OK in quoted labels**: `A["Ação"]` works, but `Ação["label"]` does NOT

### 2. Node ID Rules

```
GOOD:  A["Comissão"]    B["Análise"]    C1["Résumé"]
BAD:   Comissão["text"]  Análise["text"]  C["text with <br/> break"]
```

### 3. Subgraphs

- **NEVER put standalone (unconnected) nodes inside a subgraph** — this causes "Unsupported markdown: list" in Obsidian
- Every node inside a subgraph MUST have at least one arrow connecting it
- If you need a list of items, use a markdown table/list OUTSIDE the diagram instead
- **`direction TB`/`LR` inside subgraphs** can cause issues — avoid when possible

```
BAD (standalone nodes in subgraph):
subgraph MyGroup["Options"]
    A["Option 1"]
    B["Option 2"]
    C["Option 3"]
end

GOOD (connected nodes):
subgraph MyGroup["Options"]
    ROOT["Options"] --> A["Option 1"]
    ROOT --> B["Option 2"]
    ROOT --> C["Option 3"]
end

BETTER (simple diagram + table):
graph LR
    X["Options"] --> Y["See table below"]

| Option | Description |
|--------|-------------|
| Option 1 | Details here |
| Option 2 | Details here |
```

### 4. Special Characters in Labels

These characters BREAK Mermaid parsing even inside quotes. Escape or avoid them:

| Character | Problem | Solution |
|-----------|---------|----------|
| `()` | Conflicts with node shape | Use `["text with parens"]` |
| `[]` | Conflicts with node shape | Use different delimiters or escape |
| `{}` | Conflicts with node shape | Wrap in quotes |
| `<>` | Arrow syntax conflict | Spell out or omit |
| `%` | Comment marker in Mermaid | Avoid in labels |
| `&` | Breaks parsing | Use "and" instead |
| `;` | Statement terminator | Avoid |
| `#` | Special meaning | Avoid in labels |
| `"` inside labels | Use `&quot;` or single quotes | `A["it's 'good'"]` |

### 5. Emojis

- Emojis render in Obsidian but **colors invert in dark mode**
- Emojis are **unreliable on GitHub**
- **Recommendation**: Avoid emojis in diagrams for cross-platform use

### 6. Style Directives

- `style NodeID fill:#hex,stroke:#hex,color:#hex` — works on all platforms
- `classDef` — works for basic styling but `classDef default` is partially broken in Obsidian
- **Recommendation**: Use explicit `style` per node, not `classDef default`
- **Never use `%%{init:}%%` directives** — unreliable on GitHub and Notion

### 7. Diagram Complexity

- **Max 50 nodes / 100 edges** for reliable rendering
- Obsidian has a ~280 edge hard limit (not configurable)
- **Max ~50,000 characters** in a single Mermaid block
- If exceeding limits: split into multiple smaller diagrams

### 8. Supported Diagram Types (Cross-Platform)

| Type | Obsidian | GitHub | Notion |
|------|----------|--------|--------|
| `graph` / `flowchart` | Yes | Yes | Yes |
| `sequenceDiagram` | Yes | Yes | Yes |
| `classDiagram` | Yes | Yes | Yes |
| `stateDiagram-v2` | Yes | Yes | Yes |
| `erDiagram` | Yes | Yes | Yes |
| `gantt` | Yes | Yes | Yes |
| `pie` | Yes | Yes | Yes |
| `gitGraph` | Yes | Yes | Yes |
| `mindmap` | Yes (v1.4+) | Yes | Yes |
| `timeline` | Yes (v1.4+) | Yes | Yes |
| `quadrantChart` | Yes | Yes | Partial |
| `xychart-beta` | Yes | Partial | Partial |
| `sankey-beta` | Yes | Partial | Partial |

### 9. Features That DO NOT Work (any platform)

- Click events / callbacks
- Hyperlinks in nodes
- Font Awesome icons (`fa:fa-*`)
- Interactive tooltips
- `%%{init:}%%` theme directives (unreliable)

---

## Templates

### Simple Flow

```
graph LR
    A["Step 1"] --> B["Step 2"]
    B --> C["Step 3"]
    C --> D["Result"]

    style A fill:#E3F2FD,stroke:#1565C0
    style D fill:#C8E6C9,stroke:#2E7D32
```

### Hierarchy with Branches

```
graph TD
    ROOT["Main Topic"] --> A["Branch A"]
    ROOT --> B["Branch B"]
    ROOT --> C["Branch C"]
    A --> A1["Detail A1"]
    A --> A2["Detail A2"]
    B --> B1["Detail B1"]

    style ROOT fill:#4285F4,color:#fff
```

### Decision Flow

```
graph TD
    START["Start"] --> Q{"Decision?"}
    Q -->|"Yes"| Y["Do This"]
    Q -->|"No"| N["Do That"]
    Y --> END["Done"]
    N --> END

    style Q fill:#FFF9C4,stroke:#F9A825
```

### Mindmap

```
mindmap
  root((Central Topic))
    Branch A
      Leaf A1
      Leaf A2
    Branch B
      Leaf B1
    Branch C
```

Note: Mindmap uses **indentation only** (no quotes, no arrows, no node shapes).
Avoid accented characters in mindmap nodes — use ASCII equivalents.

### Pie Chart

```
pie title Distribution
    "Category A" : 40
    "Category B" : 30
    "Category C" : 20
    "Category D" : 10
```

### Sequence Diagram

```
sequenceDiagram
    participant A as Client
    participant B as Server
    participant C as Database
    A->>B: Request
    B->>C: Query
    C-->>B: Result
    B-->>A: Response
```

### Timeline

```
timeline
    title Project Timeline
    2025-01 : Phase 1 launched
    2025-03 : Phase 2 development
    2025-06 : Beta release
    2025-09 : General availability
```

---

## Fix Mode

When the user says `/mermaid fix <file>`, do the following:

1. Read the file
2. Find all ` ```mermaid ` blocks
3. Check each block for violations of the rules above
4. Fix all issues:
   - Replace `<br/>` and `<br>` with ` ` (space) or split into separate nodes
   - Remove standalone nodes from subgraphs (move to connected graphs or tables)
   - Quote all unquoted labels with special characters
   - Replace accented node IDs with ASCII
   - Remove `direction TB`/`LR` from subgraphs if causing issues
   - Remove emojis if targeting cross-platform
   - Move complex label text to markdown tables
5. Show the user a summary of what was fixed

---

## Platform-Specific Notes

### Obsidian
- Bundled Mermaid v11.4.x (as of 2025)
- Dark mode inverts emoji colors (known bug, won't fix)
- CSS snippet to prevent diagram cropping: `.markdown-preview-view .mermaid svg { max-width: 100%; }`
- No way to configure `maxEdges` natively

### GitHub
- Renders in fenced code blocks in files, issues, PRs, discussions
- Does NOT render in Wikis
- Hyperlinks and click events stripped for security
- Some emoji and extended ASCII break rendering

### Notion
- Native support via Code block with `mermaid` language
- Toggle between code, diagram, or split view
- Narrow column width constrains diagram size
- PDF export inconsistent
