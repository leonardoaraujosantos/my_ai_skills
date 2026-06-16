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
- Avoid when possible code with high cognitive complexity (use the skill)
- Write clean, readable, easy to maintain and extend code
- Follow existing project conventions
- Add comments only when logic is not self-evident
- The code need to be maintainable by humans and agents
- All the PRs need to have a good, descriptive message.
- Any bug found need to have a regression test added on the PR that solve the issue
- Before claims like it was not working before, do check against your changes
- All the PRs need to update the project documentation or openspec when necessary

## Verification

- Before claiming any issue is pre-existing, verify on the main branch first
- Always diff linter/type-check/test results against main before stating errors are not yours

## Communication

- Be concise and direct
- Avoid unnecessary pleasantries or filler words
