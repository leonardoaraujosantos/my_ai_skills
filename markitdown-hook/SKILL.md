---
name: markitdown-hook
description: >
  Install a harness-level PreToolUse(Read) hook that auto-converts binary
  documents (PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS, EPub) to Markdown before
  Claude reads them, saving tokens. Claude's built-in Read renders PDF pages as
  images at high token cost; this hook intercepts the Read, converts the file
  locally with markitdown to a sibling .converted.md, and redirects the read
  there. Use when the user wants to set up automatic document-to-Markdown
  conversion, reduce token cost on PDFs/Office docs, or asks to install/manage
  the markitdown read interceptor. One-time install per machine.
metadata:
  version: 1.0.0
  category: tooling
  source: "Adapted from vakaobr/claude-code-ai-development-workflow (markitdown interceptor)"
---

# markitdown-hook — Auto-convert documents to Markdown on Read

A `PreToolUse(Read)` hook that makes reading binary documents cheap. When Claude
calls `Read` on a `.pdf/.docx/.doc/.pptx/.ppt/.xlsx/.xls/.epub`, the hook
converts it locally to a sibling `<name>.converted.md` and **blocks the original
Read**, redirecting Claude to the Markdown — *before* the binary is loaded, so no
tokens are spent on it. `Read` otherwise renders PDF pages as images (very
expensive, not greppable); Markdown is ~an order of magnitude cheaper and
diffable.

This complements the manual `convert-to-md` / `pdf-tools` skills — those are
on-demand; this is automatic on every `Read`.

## When to Use

- The user wants automatic, token-saving document conversion across all projects.
- The user asks to install, re-install, verify, or remove the markitdown Read hook.

## Install

```bash
bash ~/.claude/skills/markitdown-hook/scripts/install.sh
```

The installer (idempotent) does three things into `~/.claude`:
1. Creates a Python venv at `~/.claude/.venvs/markitdown` with `markitdown[all]`
   (needs Python **3.10–3.13**; auto-detects a compatible interpreter).
2. Copies the hook to `~/.claude/hooks/markitdown-read.sh`.
3. Registers a `PreToolUse(Read)` hook in `~/.claude/settings.json` (safe merge —
   only adds the entry if missing).

**After install: restart Claude Code** (hooks load at startup), then run `/hooks`
to confirm `PreToolUse → Read → ~/.claude/hooks/markitdown-read.sh`.

## How it works & safety

- **Documents only.** Images/audio/zip are NOT intercepted — auto-OCRing an image
  would strip the visual the user likely wanted. Use `convert-to-md` for those.
- **Best-effort & non-fatal.** Any miss (no converter, conversion error,
  oversized, missing file) exits 0 → the original `Read` proceeds unchanged.
- **Cached** — reuses an up-to-date `.converted.md`. **Size-guarded** — skips
  files >50 MB (decompression-bomb guard). **Never clobbers** — always writes
  `<name>.converted.md`.
- **Sensitive-path guard** — never converts files under `.ssh/`, `.aws/`,
  `.gnupg/`, `.claude/`, `credentials.json`, or `*.env`.
- **Prompt-injection aware** — the redirect message tells Claude to treat the
  converted text as untrusted data, never instructions.

## Known limitation

This catches *model-initiated* `Read` calls, **not** files you drag-drop or paste
as a bare path — Claude Code attaches those through an internal pipeline that
bypasses the `Read` tool, so no hook can intercept it. For a dropped document,
ask *"read /path/file.docx"* (routes through `Read`) or convert it manually.

## Files

- `hooks/markitdown-read.sh` — the interceptor (installed to `~/.claude/hooks/`)
- `scripts/install.sh` — idempotent installer

## Debugging

Set `MARKITDOWN_HOOK_DEBUG=1` to log hook activity to
`~/.claude/markitdown-hook.log`. To remove: delete the `PreToolUse`/`Read` entry
in `~/.claude/settings.json` and restart Claude Code.
