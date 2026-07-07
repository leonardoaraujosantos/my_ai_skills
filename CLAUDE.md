# Project Rules — my_ai_skills

This repo is the source of truth for Claude Code skills. Skills are installed by copying to `~/.claude/skills/`.

## Adding or changing a skill

- Each skill is `<name>/SKILL.md` with frontmatter: `name:` matching the directory exactly, a `description:` including "Use when ..." trigger phrases, and an `argument-hint:`.
- Scripts are Python 3 stdlib-only CLIs with argparse subcommands. Smoke-test them for real before committing (known reference values for calculators).
- README parity is enforced by CI: every skill needs a row in the Skills Overview table AND a body section, both in alphabetical order.
- Run `python3 scripts/validate_skills.py` before opening a PR.
- After merging, copy the skill to `~/.claude/skills/`.

## Repo conventions

- PRs are squash-merged with descriptive bodies; commits are concise and technical; never mention AI in commits or PRs.
- `global/CLAUDE.md` is a distributable template for a user's global `~/.claude/CLAUDE.md` — it is NOT this repo's project instructions. Install/update it with `bash scripts/install_global_claude.sh`.
