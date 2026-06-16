# Global Rules

## Git Commits

When creating git commits:

- Do NOT include "Co-Authored-By: Claude" or any mention of Claude or AI in commit messages
- Write commit messages as if written by the developer
- Keep commit messages concise and technical
- Focus on what changed and why
- Dont mention Claude even when you create PRs.

## Code Style

- When possible / available use OpenSpec and it's skills, CLI
- Avoid when possible code with high cognitive complexity (use the skill; see targets below)
- Write clean, readable, easy to maintain and extend code
- Follow existing project conventions
- Add comments only when logic is not self-evident
- The code need to be maintainable by humans and agents
- All the PRs need to have a good, descriptive message.
- Any bug found need to have a regression test added on the PR that solve the issue
- Before claims like it was not working before, do check against your changes
- All the PRs need to update the project documentation or openspec when necessary

## Cognitive Complexity Targets

Acceptable per-function cognitive complexity depends on the domain (measure with the `cognitive-complexity` skill):

| Domain | Max per function | Notes |
|--------|------------------|-------|
| Frontend (components, hooks, UI state) | 8–12 | Extract custom hooks; use `.map`/`.filter`; keep presentation and algorithm separate |
| Backend services (APIs, business logic) | 15 | SonarQube default; guard clauses, push rules into service/use-case classes |
| Compilers / parsers / systems | 25–35+ | AST traversal, recursion, large pattern matches; isolate with the Visitor pattern and document; still split above ~35 |

General bands (any domain): 0–10 excellent, 11–15 acceptable, 16–25 warning, 26+ critical. These are guidance, not hard gates — a genuinely irreducible algorithm may exceed them; flag it rather than mangling it to satisfy a number.

## Verification

- Before claiming any issue is pre-existing, verify on the main branch first
- Always diff linter/type-check/test results against main before stating errors are not yours

## Communication

- Be concise and direct
- Avoid unnecessary pleasantries or filler words
