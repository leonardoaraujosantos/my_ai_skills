---
name: openspec
description: Spec-driven development with OpenSpec. Discuss a feature then spec it before coding (proposal/specs/design/tasks); implement against the artifacts, validate, and archive so living specs stay in the repo. Use for medium/large features or any auth/billing/security/data-model/full-stack change. To onboard an existing (brownfield) codebase onto OpenSpec, use the openspec-baseline skill instead. Triggers — "use openspec", "spec this out", "propose a change", "discuss the project", "/opsx", "openspec".
argument-hint: [discuss|propose|apply|baseline|status|validate|archive|init] [change-name]
---

# OpenSpec — Spec-Driven Development

OpenSpec is a lightweight, open-source framework for spec-driven development with coding agents. No API key, no MCP. Instead of "implement X" straight to code, you create a **specified change** first: a folder with a proposal, spec deltas, design, and tasks. You then implement against those artifacts — the intent lives in the repo, not in chat history.

CLI is already installed globally (`openspec`, v1.4.x, requires Node ≥ 20.19). Reinstall/upgrade only if a command is missing: `npm install -g @fission-ai/openspec@latest`.

## When to use OpenSpec

| Situation | Action |
|-----------|--------|
| Small, obvious fix (typo, one-line bug) | Skip OpenSpec — edit directly |
| Medium/large feature | Use OpenSpec |
| Auth / billing / permissions / security | **OpenSpec required** |
| Data-model / schema / migration change | **OpenSpec required** |
| Frontend + backend + agent in one change | **OpenSpec required** |

The point isn't bureaucracy — it's spending 10–20 min aligning intent to save hours fixing a wrong implementation. If a request clearly falls in a "required" row and the user hasn't mentioned OpenSpec, suggest it before coding.

## Mental model

```
Idea → Proposal → Spec delta → Design → Tasks → Implement → Validate → Archive → Official spec updated
```

Artifacts for a change live in `openspec/changes/<change-name>/`: `proposal.md`, `design.md`, `tasks.md`, and `specs/`. On archive, the spec deltas merge into `openspec/specs/` (the source of truth) and the change folder moves to `openspec/changes/archive/YYYY-MM-DD-<name>/`.

## Workflow

### 0. Ensure the project is initialized

Check for an `openspec/` directory at the repo root. If absent, initialize it (this also generates the `/opsx:*` slash commands for the chosen tools):

```bash
openspec init --tools claude          # or: claude,cursor,codex  |  --tools all
```

Creates:
```
openspec/
├── specs/        # official specs — source of truth, versioned with code
├── changes/      # proposed / in-progress changes
└── config.yaml   # project config (active profile / schema)
```
Treat `openspec/` as part of the repo and commit it.

### 1. Propose a change

Two paths — prefer the slash command inside an agent session, fall back to the CLI to scaffold the folder:

```bash
openspec new change add-magic-link-login \
  --description "Login via one-time email link"
```
Useful `new change` flags: `--description <text>`, `--goal <text>`, `--areas <names>`, `--schema <name>` (default `spec-driven`).

Inside Claude Code / Cursor / Codex, the richer path is the generated command:
```
/opsx:propose Add magic link login. User enters email, gets a single-use link,
token expires in 15 min, backend creates a session if the token is valid.
```
This has the agent generate proposal + spec deltas + design + tasks. Keep scope tight in the prompt ("don't implement billing yet") — the spec becomes the scope contract.

Core profile workflows: `/opsx:propose`, `/opsx:explore`, `/opsx:apply`, `/opsx:sync`, `/opsx:archive`. (Expanded profiles add `/opsx:new`, `/opsx:continue`, `/opsx:ff`, `/opsx:verify`, `/opsx:bulk-archive`, `/opsx:onboard` — enable via `openspec config profile` then `openspec update`.)

### 2. Review the artifacts before implementing

```bash
openspec list                          # active changes
openspec list --specs                  # existing specs
openspec show add-magic-link-login     # change detail (--json for tooling)
openspec status --change add-magic-link-login    # per-artifact progress
openspec validate add-magic-link-login           # structural check
```

`openspec instructions` returns what to build next for an agent (template, project context, dependencies, per-artifact rules):
```bash
openspec instructions --change add-magic-link-login          # next artifact
openspec instructions design --change add-magic-link-login   # specific artifact
openspec instructions apply  --change add-magic-link-login   # implementation guidance
```

### 3. Implement

Use `/opsx:apply`, or feed `openspec instructions apply --change <name>` to the agent and instruct: **"Implement exactly the tasks in this change. Do not change scope outside the OpenSpec change."** Stay inside the tasks list; if something genuinely needs to grow, update the change's spec/tasks first rather than silently expanding scope.

### 4. Validate before the PR

```bash
openspec validate --all --strict
# then the project's own gate, e.g. pytest / npm test / go test
```

### 5. Archive after merge

```bash
openspec archive add-magic-link-login --yes        # merges deltas into openspec/specs/, moves to archive/
openspec archive update-ci-config --skip-specs     # tooling/infra/doc-only change with no spec impact
```

## Discuss first, then spec (greenfield / new feature)

Don't jump straight to `/opsx:propose` for anything non-trivial. Run a short alignment conversation, then encode the agreed intent into the proposal so the spec captures decisions instead of guesses.

1. **Discuss** — ask the user (or work it out together) and capture:
   - Goal / the problem being solved, and who it's for.
   - **Non-goals** — what's explicitly out of scope (this becomes the scope guardrail).
   - Constraints: stack, data model, auth model, performance, deadlines.
   - Key decisions and their rationale (e.g. "magic link not password — fewer support tickets").
   - Open questions to resolve before coding.
   For open-ended exploration, `/opsx:explore <topic>` lets the agent investigate options before committing.
2. **Confirm** the scope back to the user in 3–5 bullets. Get a yes.
3. **Propose** — feed that agreed context into the proposal:
   ```
   /opsx:propose <paste the goal, constraints, and explicit non-goals from the discussion>
   ```
   or scaffold via CLI and fill artifacts: `openspec new change <name> --description "..." --goal "..."`.
4. **Review** the generated `proposal.md` / `design.md` / `tasks.md` *with the user* before `/opsx:apply`. The cheapest place to fix a misunderstanding is the spec, not the code.

Rule of thumb: spend 10–20 min aligning intent to save hours fixing a wrong build. The discussion is the work; the proposal is the receipt.

## Baseline specs from an existing codebase (brownfield)

OpenSpec is brownfield-first: on a project that's *already built* you reverse-engineer specs from the implementation (an agent-driven read-and-document pass — there's no CLI that auto-generates specs from code), writing each capability directly to `openspec/specs/<capability>/spec.md` in `### Requirement: … SHALL …` + `#### Scenario:` form, then `openspec validate --specs`.

**For the full end-to-end onboarding — initialize `openspec/`, reverse-engineer capability-scoped baseline specs, add an `openspec-validate` CI job, and open a PR — use the dedicated `openspec-baseline` skill.** Use the manual pass here only when you want a spec or two without the whole CI/PR machinery.

## Writing good specs

Use requirement language with SHALL + scenarios. Be testable and unambiguous.

```markdown
### Requirement: Magic link login
The system SHALL allow a user to request a one-time login link by email.

#### Scenario: Valid magic link
- GIVEN a user requested a magic link
- AND the token has not expired
- WHEN the user opens the link
- THEN the system SHALL create an authenticated session
- AND the token SHALL be invalidated
```

Avoid vague specs ("the system should have modern, secure login"). Prefer concrete, enforceable statements:
```
The system SHALL issue single-use login tokens.
The token SHALL expire after 15 minutes.
The token SHALL be invalidated after successful use.
The system SHALL NOT reveal whether an email exists during a login request.
```

Split a large change into capability-scoped spec deltas so the agent can't bleed scope:
```
openspec/changes/add-idea-box-board/specs/
├── realtime-collaboration/spec.md
├── board-stickers/spec.md
├── ai-context-agent/spec.md
└── permissions/spec.md
```

## Daily command cheat sheet

```bash
openspec list                                   # open changes
openspec list --specs                           # existing specs
openspec show <change>                           # change/spec detail (autodetects type)
openspec new change <name> --description "..."   # scaffold a change
openspec status --change <name>                  # artifact progress
openspec validate <name>                         # validate one change
openspec validate --all --strict                 # validate everything (use in CI)
openspec instructions apply --change <name>      # next-step guidance for the agent
openspec archive <name> --yes                    # archive + update specs
openspec view                                     # interactive TUI dashboard
openspec update                                   # regenerate tool files after upgrade/profile change
```

## Config & telemetry

```bash
openspec config list                         # current config (path/get/set/unset/reset/edit/profile)
openspec config path
openspec config set telemetry.enabled false  # or: export OPENSPEC_TELEMETRY=0  /  DO_NOT_TRACK=1
openspec config profile                      # pick workflow profile, then `openspec update`
```
Env vars: `OPENSPEC_TELEMETRY`, `DO_NOT_TRACK`, `OPENSPEC_CONCURRENCY`, `EDITOR`/`VISUAL`, `NO_COLOR`.

## CI gate (recommended)

```yaml
name: OpenSpec Validate
on: [pull_request, push]
jobs:
  openspec:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm install -g @fission-ai/openspec@latest
      - run: openspec validate --all --strict
```

## Reference

- Docs: https://openspec.dev
- Source: https://github.com/Fission-AI/OpenSpec
- Install: `npm install -g @fission-ai/openspec@latest`
