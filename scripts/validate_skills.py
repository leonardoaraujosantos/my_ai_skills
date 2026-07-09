#!/usr/bin/env python3
"""Validate each skill's SKILL.md frontmatter and docs/README parity.

Checks (hard errors, exit 1):
  * every <skill>/SKILL.md has a frontmatter block
  * frontmatter `name:` matches the directory name
  * frontmatter has a non-empty `description:`
  * every skill directory has a row in the docs/SKILLS.md table (alphabetical),
    and the table lists no skill that doesn't exist
  * every skill appears in the README "Skills at a Glance" mermaid mindmap,
    and the mindmap lists no skill that doesn't exist
  * every skill has a `## <name>` body section in the README

Warnings (exit 0): missing `argument-hint`.

Stdlib only so it runs in CI without installing anything.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return text[3:end]


def top_level_keys(frontmatter: str) -> dict:
    keys = {}
    for line in frontmatter.splitlines():
        if not line or line[0].isspace():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):(.*)$", line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def main() -> int:
    errors, warnings = [], []

    skill_dirs = sorted(p.parent.name for p in ROOT.glob("*/SKILL.md"))
    if not skill_dirs:
        print("No skills found — is this the repo root?", file=sys.stderr)
        return 1

    for name in skill_dirs:
        fm = read_frontmatter(ROOT / name / "SKILL.md")
        if fm is None:
            errors.append(f"{name}/SKILL.md: missing or malformed frontmatter block")
            continue
        keys = top_level_keys(fm)
        if keys.get("name") != name:
            errors.append(f"{name}/SKILL.md: name '{keys.get('name')}' does not match directory '{name}'")
        if not keys.get("description"):
            errors.append(f"{name}/SKILL.md: missing 'description'")
        if "argument-hint" not in keys:
            warnings.append(f"{name}/SKILL.md: no 'argument-hint'")

    # docs/SKILLS.md — the complete overview table
    skills_doc = ROOT / "docs" / "SKILLS.md"
    if not skills_doc.exists():
        errors.append("docs/SKILLS.md: file is missing")
        rows = []
    else:
        rows = re.findall(
            r"^\|\s*\[([a-z0-9-]+)\]\(\.\./README\.md#", skills_doc.read_text(encoding="utf-8"), re.MULTILINE
        )
    listed = set(rows)
    for name in skill_dirs:
        if name not in listed:
            errors.append(f"docs/SKILLS.md: skill '{name}' missing from the Skills Overview table")
    for name in sorted(listed):
        if name not in skill_dirs:
            errors.append(f"docs/SKILLS.md: table lists '{name}' but there is no such skill directory")
    if rows != sorted(rows):
        errors.append("docs/SKILLS.md: table rows are not in alphabetical order")

    # README.md — mindmap and per-skill body sections
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    mindmap_match = re.search(r"```mermaid\s*\nmindmap\n(.*?)```", readme, re.DOTALL)
    if not mindmap_match:
        errors.append("README.md: 'Skills at a Glance' mermaid mindmap block not found")
    else:
        mindmap_nodes = set(re.findall(r"^\s+([a-z0-9-]+)$", mindmap_match.group(1), re.MULTILINE))
        for name in skill_dirs:
            if name not in mindmap_nodes:
                errors.append(f"README.md: skill '{name}' missing from the mindmap")
        for name in sorted(mindmap_nodes):
            if name not in skill_dirs:
                errors.append(f"README.md: mindmap lists '{name}' but there is no such skill directory")

    sections = set(re.findall(r"^## ([a-z0-9-]+)\s*$", readme, re.MULTILINE))
    for name in skill_dirs:
        if name not in sections:
            errors.append(f"README.md: skill '{name}' has no '## {name}' body section")

    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)

    print(f"\n{len(skill_dirs)} skills checked, {len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
