---
name: openspec-baseline
description: Onboard an existing codebase onto OpenSpec end-to-end - initialize openspec/, reverse-engineer capability-scoped baseline specs from the current implementation (code, tests, docs, ADRs), add an openspec-validate job to CI, and open a PR. Use on brownfield projects that have no openspec/ directory yet, or when asked to "create the openspec of this project", "baseline this codebase", "document current behavior as specs", or "add openspec validation to CI".
argument-hint: [optional focus areas or "no-pr" to skip the PR]
---

# OpenSpec Baseline — Onboard an Existing Codebase

Reverse-engineer living specs from an existing project and wire validation into CI, ending with a reviewable PR. This complements the `openspec` skill (general spec-driven workflow); this one is specifically the brownfield onboarding play.

Prerequisite: `openspec` CLI installed globally (`npm install -g @fission-ai/openspec@latest`, Node >= 20.19).

## Outcome

1. `openspec/` initialized and committed.
2. `openspec/specs/<capability>/spec.md` baseline specs describing **observed** behavior (not aspirations), validated with `openspec validate --specs --strict`.
3. A CI job running `openspec validate --all --strict` on PRs and pushes to the default branch.
4. A PR whose description inventories the capabilities AND lists open questions / suspected bugs found while documenting.

## Step 1 — Recon and init

- Read the repo top-level: README, any TRD/PRD/CONTEXT/GLOSSARY docs, `docs/adr/` if present, the dependency manifest, and the directory tree of the main source package.
- If the project defines a ubiquitous language (glossary/CONTEXT doc), **use its exact terms** in the specs and respect its "avoid" lists.
- `openspec init --tools claude` (skip if `openspec/` exists — then only add missing baseline specs).

## Step 2 — Map capabilities with parallel exploration

Dispatch parallel Explore agents (read-only), one per subsystem, sized to the repo. Typical split for a service:

1. **Public surface** — HTTP routes, CLI commands, MCP/gRPC/GraphQL, request/response schemas, validation rules, auth.
2. **Domain / lifecycle** — entities, state machines, use cases, DB models + migrations, error taxonomy, retention.
3. **Core engine** — the thing the service actually does (extraction, billing, rendering...), its strategies/backends/options and defaults.
4. **Infrastructure** — queues, storage, config/env vars with defaults, deployment manifests, entry points, observability.
5. **Tests + docs** — ALL BDD/feature files (they encode intent), key unit-test contracts, TRD/ADRs, README claims.

Instruct every agent to: report request/response contracts, allowed values, defaults, limits, and edge cases; cite `file:line` for each claim; return raw structured markdown, not prose. Mine tests hard — they are the closest thing to intended behavior.

## Step 3 — Write baseline specs

Write directly to `openspec/specs/<capability>/spec.md` (NOT as change deltas — you are recording what exists). Split by user-meaningful capability (8-12 specs for a mid-size service), e.g. `job-submission`, `job-lifecycle`, `webhook-notifications`, `storage-backends`, `service-configuration` — never by file/layer.

Format each spec:

```markdown
# <Capability Title>

## Purpose
2-4 sentences: what this capability is and its key architectural decision (cite ADRs if any).

## Requirements

### Requirement: <name>
The system SHALL <testable, unambiguous statement>. (src: path/to/file.py:42)

#### Scenario: <name>
- **GIVEN** ...
- **WHEN** ...
- **THEN** the system SHALL ...
```

Rules:
- Every requirement gets >= 1 scenario; base scenarios on real tests where they exist and cite the feature file.
- Concrete and enforceable: "SHALL expire after 15 minutes", not "should be secure".
- Document defaults, allowed values, limits, and error messages verbatim.
- Cross-cutting invariants (privacy rules, "field X never exposed") get their own requirement in the most relevant spec.
- **Do not bless bugs silently.** Where current behavior looks accidental (stuck states, bypassable validation, stale templates, doc/test mismatches), spec it as-is but record it in an "open questions" list for the PR body.
- Stub/placeholder functionality: spec it but say "currently unimplemented/stub" explicitly.

Validate until clean: `openspec validate --specs --strict`.

## Step 4 — CI validation job

Detect the CI system and add a job running `openspec validate --all --strict` (`--all` also covers future `openspec/changes/`). Prefer a **standalone workflow** over editing a shared/templated pipeline. Match the repo's existing workflow style (quoting, runner labels, naming).

GitHub Actions template (`.github/workflows/openspec-validate.yaml`):

```yaml
name: OpenSpec Validate

on:
  workflow_dispatch:
  pull_request:
    branches: ["main"]
  push:
    branches: ["main"]

concurrency:
  group: "${{ github.workflow }}-${{ github.ref }}"
  cancel-in-progress: true

jobs:
  validate:
    name: "openspec-validate"
    runs-on: "ubuntu-24.04"
    steps:
      - uses: "actions/checkout@v4"
      - uses: "actions/setup-node@v4"
        with:
          node-version: 22
      - name: "Install OpenSpec CLI"
        run: "npm install -g @fission-ai/openspec@latest"
      - name: "Validate specs and changes"
        run: "openspec validate --all --strict"
```

GitLab CI equivalent: a `openspec-validate` job in `.gitlab-ci.yml` using `image: node:22`, same two commands. No CI system found: note it in the PR and skip.

Always run the exact CI command locally before pushing.

## Step 5 — Branch, commit, PR

Unless the user passed `no-pr` or asks otherwise:

- Branch: `add-openspec-baseline-specs`. Commit `openspec/` and the CI workflow (separate commits are fine). Never commit junk files (`.DS_Store` etc.).
- Follow the user's global commit rules (no AI attribution; concise technical messages).
- PR body structure:
  1. **Summary** — adopting OpenSpec; N capability specs, M requirements; specs describe current behavior, mined from code/tests/docs.
  2. **Capabilities covered** — table of spec -> what it covers.
  3. **CI** — the new workflow + local validation output.
  4. **Open questions surfaced while documenting** — numbered list of suspected bugs/ambiguities found in Step 3. This is the most valuable review section; never omit it.
  5. **Notes** — docs-only, no runtime code touched.
- After creating the PR, check that the new CI job actually ran and passed (`gh pr checks`).

## Final report to the user

State: spec count / requirement count, validation result, PR URL, CI check status, and the open-questions list (these may warrant follow-up `/opsx:propose` changes rather than staying spec'd as-is).
