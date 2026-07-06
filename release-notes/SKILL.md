---
name: release-notes
description: Generate a changelog / release notes from git history between two refs — resolves the range, gathers commits and merged PRs, categorizes changes, writes Keep-a-Changelog markdown, suggests a semver bump, and optionally updates CHANGELOG.md or drafts a GitHub release. Use when the user asks to "generate release notes", write a "changelog", answer "what changed since the last release/tag", "prepare the vX.Y.Z release", or "draft the GitHub release".
argument-hint: "[from-ref] [to-ref] [--tag vX.Y.Z] [--audience users|developers]"
---

# Release Notes

Generate release notes / a changelog from git history between two refs, then
optionally prepend to CHANGELOG.md and create a **draft** GitHub release.

Arguments: `[from-ref] [to-ref] [--tag vX.Y.Z] [--audience users|developers]`.
Audience defaults to `users`.

## 1. Resolve the range

- Explicit refs win: if the user gave `from` (and optionally `to`), use
  `from..to` (default `to` = `HEAD`).
- Otherwise default to the last tag:

```bash
git describe --tags --abbrev=0   # -> vX.Y.Z
# range: $(git describe --tags --abbrev=0)..HEAD
```

- If no tags exist, ask the user: full history, or a `--since` date
  (`git log --since=<date>`). Do not silently pick one.
- Confirm the range is non-empty (`git rev-list --count <range>`); if zero,
  say so and stop.

## 2. Gather the raw material

```bash
git log --no-merges --pretty='%h|%s|%an|%ad' --date=short <range>
git diff --stat <range>          # scale context: files touched, +/- lines
```

Find merged PRs in the range:

- Commit-message references: subjects ending in `(#123)` (squash merges) map
  commits to PRs directly.
- Or query GitHub: `gh pr list --state merged --search "merged:>=<from-date>"
  --json number,title,labels,url --limit 200`, then intersect with the range.
- Fetch PR titles/labels for anything referenced:
  `gh pr view 123 --json title,labels,body`.

If `gh` hangs or times out, use the **github** skill's resilient API path
(read `~/.claude/skills/github/SKILL.md`): run
`~/.claude/skills/github/ghx.sh doctor` to diagnose, then
`~/.claude/skills/github/ghx.sh api repos/OWNER/REPO/pulls/123` (mirrors
`gh api` paths, auto-falls back to `curl --resolve`). Detect `OWNER/REPO`
from `git remote get-url origin`.

## 3. Categorize every change

Use conventional-commit prefixes when present:

| Prefix | Category |
|--------|----------|
| `feat` | Features |
| `fix` | Fixes |
| `perf` | Performance |
| `docs` | Documentation |
| `refactor`, `chore`, `ci`, `test`, `build` | Internal/Maintenance |
| `BREAKING CHANGE` / `!` suffix (`feat!:`) | Breaking Changes |

Breaking Changes always come first and are called out loudly.

Without a prefix, infer the category from the commit message; when the message
is ambiguous, look at the touched files (`git show <hash> --stat`) — e.g.
changes only under `docs/` are Documentation, only under `.github/` or CI
configs are Internal.

Drop noise entirely: version-bump commits, lockfile-only changes, merge
commits (already excluded by `--no-merges`), and empty "wip"-style commits
folded into a PR you already list.

## 4. Write the notes (Keep-a-Changelog flavored)

```markdown
## [vX.Y.Z] - YYYY-MM-DD

### Breaking Changes
- <what breaks and how to migrate> (#123)

### Added
- <user-visible outcome first> (#124)

### Fixed
### Changed
### Performance
### Docs
```

- Only include sections that have entries.
- Each bullet leads with the user-visible outcome, not the implementation;
  append the `(#PR)` reference when known.
- `--audience users` (default): outcome-focused wording, hide internal
  refactors/maintenance entirely.
- `--audience developers`: include Internal/Maintenance entries and append
  commit hashes (`abc1234`) alongside PR refs.

## 5. Version suggestion

If `--tag` was not given, propose a semver bump derived from the content:

- Any Breaking Change -> **major**
- Any feature -> **minor**
- Otherwise -> **patch**

State the proposed tag (e.g. "last tag v1.4.2 + fixes only -> propose
v1.4.3") and **ask the user to confirm** before using it in the heading,
CHANGELOG.md, or a release.

## 6. Deliver

1. Show the rendered notes in the conversation.
2. Only on request:
   - **CHANGELOG.md**: prepend the new section under the header, above the
     previous release. If the file doesn't exist, create it with a
     Keep-a-Changelog header:

     ```markdown
     # Changelog

     All notable changes to this project are documented in this file.
     The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
     ```

   - **GitHub release (draft only)**: write the notes to a temp file, then
     `gh release create <tag> --draft --title "<tag>" --notes-file <file>`.
     Never publish a non-draft release and never push a tag without explicit
     user approval. If `gh` hangs, fall back to the github skill's
     `ghx.sh api repos/OWNER/REPO/releases -X POST -d '{"tag_name":"<tag>","draft":true,...}'`.

## Style rules

- No AI/Claude mentions anywhere in the output — notes, CHANGELOG.md,
  release body, or commit messages.
- Concise, technical, developer-written voice.
- When a commit message is vague ("fix stuff"), verify the claim against the
  actual diff (`git show <hash> --stat`, and the patch if needed) before
  writing the bullet — describe what actually changed.
