---
name: lit-review
description: "Systematic literature review — gather papers (local PDFs or paper search), extract structured findings per paper, build a literature matrix, surface agreements/contradictions, and synthesize a cited survey note into the Obsidian vault. Use when the user says 'literature review', 'compare these papers', 'survey the research on X', 'merge ideas from these papers/documents', 'what does the literature say about', or 'build a reading list'."
argument-hint: <topic | folder-of-pdfs | paper-urls> [--depth quick|thorough] [--no-save]
---

# Lit Review

Run a systematic literature review: scope the question, gather papers, extract
structured findings per paper, build a literature matrix, analyze agreements
and contradictions across papers, and synthesize a fully cited survey note into
the Obsidian vault.

## Configuration

This skill writes to your Obsidian vault. Set these in your shell profile
(same convention as the `obsidian` and `study-this` skills):

```bash
export OBSIDIAN_VAULT="$HOME/path/to/your-vault"   # local vault repo path
export OBSIDIAN_VAULT_NAME="YourVault"             # vault name used by the Obsidian CLI
```

Optional Obsidian CLI for ranked vault search (skip if not installed):

```bash
CLI="/Applications/Obsidian.app/Contents/MacOS/Obsidian"
# invoke as: $CLI search vault="$OBSIDIAN_VAULT_NAME" query="<keywords>"
```

---

## Step 1: Scope

Before gathering anything:

1. Restate the research question in one sentence and confirm it with the user
   if the request is ambiguous.
2. Agree on inclusion criteria:
   - **Topic bounds** — what's in scope, what's explicitly out.
   - **Year range** — default: last 5 years unless the field moves slowly or
     the user asks for foundational work.
   - **N papers** — default **5-8** for `--depth quick` (the default),
     **12-20** for `--depth thorough`.

State the criteria back in a short block before proceeding. Everything gathered
later must pass these criteria or be explicitly flagged as out-of-scope context.

## Step 2: Gather

Use whichever sources apply — they combine:

**Local PDFs** — the user points at a folder or files:
- Read the PDFs directly. If the `markitdown-hook` is installed, the Read is
  auto-converted to Markdown (cheap). Fallbacks: the `convert-to-md` skill, or
  `pdf-tools` to extract text.
- Treat the file set as the candidate pool; still apply the Step 1 criteria.

**Paper search** — when the firecrawl research MCP tools are connected:
- Load schemas first via ToolSearch:
  `select:mcp__firecrawl-mcp__firecrawl_research_search_papers,mcp__firecrawl-mcp__firecrawl_research_read_paper,mcp__firecrawl-mcp__firecrawl_research_related_papers,mcp__firecrawl-mcp__firecrawl_research_inspect_paper`
- Then: `firecrawl_research_search_papers` to find candidates,
  `firecrawl_research_inspect_paper` to check metadata/abstract before
  committing, `firecrawl_research_read_paper` to read full text,
  `firecrawl_research_related_papers` for neighbors.
- If those tools are absent, fall back to WebSearch/WebFetch against arXiv
  (`arxiv.org/abs/...`, full text at `arxiv.org/pdf/...`) and Semantic Scholar
  (`semanticscholar.org`).

**Snowballing** — `--depth thorough` only:
- After the first pass, pick the 2-3 most central papers (most cited by the
  others, or most directly on the question) and follow their references and
  citations **one hop** (`firecrawl_research_related_papers` or the paper's
  reference list). Add hits that pass the inclusion criteria, up to the N cap.

Keep a running candidate list with include/exclude decisions and a one-line
reason for each exclusion.

## Step 3: Extract Per Paper

For every included paper, extract into this fixed schema — do not improvise
fields:

| Field | Content |
|-------|---------|
| **Citation** | authors, year, venue |
| **Research question** | what the paper is actually asking |
| **Method / approach** | design, model, procedure |
| **Key claims** | verbatim-grounded, each with a section or page anchor (e.g. "§4.2", "p. 7") |
| **Main results** | numbers quoted exactly when given (metrics, effect sizes, CIs) |
| **Limitations** | only those **stated by the authors** |
| **Relevance** | how it bears on the user's research question |

Save one note per paper to the vault at
`$OBSIDIAN_VAULT/Papers/<first-author-year-shortname>.md`
(e.g. `Papers/vaswani-2017-attention.md`) with YAML frontmatter:

```markdown
---
title: <full paper title>
authors: [<Author One>, <Author Two>]
year: <YYYY>
venue: <conference/journal or arXiv>
url: <url or doi>
tags: [paper, <topic-tag>]
---

# <Title>

## Research Question
## Method
## Key Claims
## Main Results
## Limitations (stated by authors)
## Relevance to: <research question>
```

**Before writing each note**, check whether it already exists
(`ls "$OBSIDIAN_VAULT/Papers/"` or Grep for the title) — if it does, **update
the existing note** rather than creating a duplicate.

## Step 4: Literature Matrix

Build one markdown table, papers as rows:

| Paper | Method | Dataset / setup | Key result | Stance on the central question |
|-------|--------|-----------------|------------|--------------------------------|

Add at most 2-3 extra columns if the domain demands it (e.g. sample size,
year) — keep the matrix **under ~8 columns** so it stays readable in Obsidian.
Every cell must be traceable to the paper's extraction note.

## Step 5: Cross-Paper Analysis

Three subsections, in this order:

1. **Agreements** — consensus claims. Each must be backed by **≥2 citations**;
   a claim from a single paper is a finding, not a consensus.
2. **Contradictions** — where papers disagree, state **both sides with
   citations**. Never average away a disagreement or pick a winner silently;
   if one side has stronger evidence, say why (sample size, replication,
   recency) and cite it.
3. **Gaps** — open questions no included paper addresses, phrased as concrete
   future-work items.

## Step 6: Synthesize the Survey Note

Compose the review note with this structure:

```markdown
---
title: "Literature Review: <topic>"
date: <YYYY-MM-DD>
papers_reviewed: <N>
tags: [literature-review, <topic-tag>]
---

# Literature Review: <Topic>

## TL;DR
<exactly 5 sentences>

## Literature Matrix
<the Step 4 table>

## Synthesis
<themed sections — organized by theme, NOT paper-by-paper — with inline
citations like (Author, 2024) on every claim>

## Contradictions
<Step 5.2, both sides cited>

## Gaps & Future Work
<Step 5.3>

## Not Reviewed
<papers that matched criteria but couldn't be read — see Rules>

## References
<full list; each entry links its vault note: [[Papers/<first-author-year-shortname>]]>
```

Save to `$OBSIDIAN_VAULT/Literature Reviews/<topic>.md` and link each paper
via `[[Papers/...]]`. **Skip all vault writes when `--no-save` is passed** —
present the review inline instead.

After saving, sync the vault with the **`obsidian` skill** (`/obsidian sync`).

## Step 7: Rules

Non-negotiable:

- **Every claim traces to a specific paper** — no uncited assertions anywhere
  in the synthesis.
- **Quote numbers exactly** as printed in the paper; no rounding, no derived
  figures presented as reported ones.
- **Paywalled / unreadable papers**: if a paper couldn't actually be read,
  list it under **"Not reviewed"** — never cite its abstract as if the full
  paper was read.
- **Ask before overwriting** an existing note in `Literature Reviews/` —
  offer to update it or write under a new name.

---

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--depth quick` | 5-8 papers, no snowballing | yes |
| `--depth thorough` | 12-20 papers, one-hop snowballing from the 2-3 most central papers | — |
| `--no-save` | Present the review inline; write nothing to the vault | off |

---

## Pairs with

- **deep-research** — the question is broader than academic papers (industry
  reports, blogs, news); run it for the web side and fold results in.
- **study-this** — queue the most important papers found here as follow-up
  reading in `Things to Study/`.
- **flashcards** — turn the survey note's key findings into spaced-repetition
  cards to retain them.
- **notebooklm** — generate a podcast/audio overview from the finished review
  note.
