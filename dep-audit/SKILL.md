---
name: dep-audit
description: Multi-ecosystem dependency audit - scan for vulnerable and outdated packages (npm, Python, Go, Rust, Ruby, PHP) and produce a prioritized upgrade plan. Reports and plans only; never mutates the project. Use when the user asks to "audit dependencies", "check for vulnerable/outdated packages", "npm audit", "CVE check", "is anything outdated", or wants an "upgrade plan".
argument-hint: [path] [--fix-plan] [--prod-only]
---

# Dependency Audit

Audit every dependency ecosystem in a project for **known vulnerabilities** and
**outdated packages**, then report — and, with `--fix-plan`, produce a
prioritized upgrade plan.

**Arguments**

| Argument | Meaning |
|----------|---------|
| `[path]` | Target directory (default: current working directory) |
| `--fix-plan` | Append an ordered upgrade plan to the report |
| `--prod-only` | Exclude dev dependencies where the tool supports it |

## Hard rules

- **NEVER run a mutating command** — no `npm audit fix`, no `npm update`,
  no `pip install -U`, no `cargo update`, no `go get -u`, no lockfile
  regeneration — without explicit user approval. This skill **reports and
  plans only**. Applying the plan is a separate, user-approved step.
- If an audit tool is missing and cannot be installed, **say so** and mark
  that ecosystem **"not scanned"** in the report. Never silently skip an
  ecosystem.
- Lockfile-less projects (e.g. only `requirements.txt` with loose pins, or
  `package.json` with no lockfile) give **weaker results** — installed
  versions may differ from declared ranges. Note this caveat in the report.
- Secrets in code, S3 buckets, IAM misconfigurations, or app-level
  vulnerabilities are **out of scope** — point the user to the `pentest`
  skill for those.

## Step 1 — Detect ecosystems

Scan the target path for manifests/lockfiles. Audit **every** ecosystem
found, and report which were detected (and which lockfile picked the tool):

| Ecosystem | Detect by | Tool selection |
|-----------|-----------|----------------|
| Node.js | `package.json` | `package-lock.json` → npm; `pnpm-lock.yaml` → pnpm; `yarn.lock` → yarn |
| Python | `requirements.txt`, `pyproject.toml`, `poetry.lock`, `uv.lock` | pip-audit (export requirements for poetry/uv first) |
| Go | `go.mod` | govulncheck |
| Rust | `Cargo.toml` (+`Cargo.lock`) | cargo-audit |
| Ruby | `Gemfile.lock` | `bundler-audit` if available, else mark not scanned |
| PHP | `composer.json` (+`composer.lock`) | `composer audit` |

Check subdirectories one level down for monorepo layouts (e.g.
`apps/*/package.json`) if nothing is found at the root.

## Step 2 — Vulnerability scan

Prefer JSON output and parse it. Run per detected ecosystem:

| Ecosystem | Command | Notes |
|-----------|---------|-------|
| npm | `npm audit --json` | `--prod-only` → add `--omit=dev` |
| pnpm | `pnpm audit --json` | `--prod-only` → add `--prod` |
| yarn | `yarn npm audit --json` | Yarn Berry; classic yarn: `yarn audit --json` |
| Python | `pip-audit --format json` | If missing, suggest `pip install pip-audit`. Poetry: `poetry export -f requirements.txt --without-hashes -o /tmp/reqs.txt` then `pip-audit -r /tmp/reqs.txt --format json`. uv: `uv export --no-hashes -o /tmp/reqs.txt` then same |
| Go | `govulncheck ./...` | If missing, suggest `go install golang.org/x/vuln/cmd/govulncheck@latest` |
| Rust | `cargo audit` | If missing, suggest `cargo install cargo-audit` |
| Ruby | `bundle exec bundler-audit check --update` | Or `gem install bundler-audit`; if unavailable, mark not scanned |
| PHP | `composer audit --format=json` | `--prod-only` → add `--no-dev` |

For each finding, extract: severity, package name, installed version,
fixed-in version, advisory ID (CVE/GHSA/RUSTSEC/GO-...), and whether the
package is a **direct** or **transitive** dependency (npm: check
`package.json`; Python: check the manifest; Go: `go.mod` require block;
Rust: `Cargo.toml`).

## Step 3 — Outdated packages

| Ecosystem | Command | Notes |
|-----------|---------|-------|
| npm | `npm outdated --json` | Non-zero exit when outdated packages exist — that is normal |
| Python (pip) | `pip list --outdated --format json` | |
| Python (poetry) | `poetry show --outdated` | Text output — parse columns |
| Python (uv) | `uv pip list --outdated` | |
| Go | `go list -u -m -json all` | Report **direct deps only** (filter `Indirect: true`); `Update` field present → outdated |
| Rust | `cargo outdated` | Only if installed; otherwise note it and skip outdated for Rust |

Classify every outdated package as a **patch**, **minor**, or **major** bump
by semver diff between installed and latest.

## Step 4 — Report

The report is the deliverable. Use exactly this structure:

### 4.1 Summary line

```
X vulnerabilities (C crit / H high / M med / L low) across N ecosystems; Y outdated packages (Z major)
```

Follow it with the detected-ecosystems line, e.g.:
`Detected: npm (package-lock.json), Python (poetry.lock), Go. Not scanned: Rust (cargo-audit unavailable).`

### 4.2 Vulnerability table

Sorted by severity (critical first):

| Severity | Package | Installed | Fixed in | Advisory | Direct/Transitive |
|----------|---------|-----------|----------|----------|-------------------|
| critical | example | 1.2.3 | 1.2.7 | CVE-2026-XXXXX | direct |

If zero vulnerabilities: state that explicitly per ecosystem.

### 4.3 Outdated table

Grouped by bump type — **Major**, then **Minor**, then **Patch** — each group
its own table:

| Package | Installed | Latest | Ecosystem |
|---------|-----------|--------|-----------|

### 4.4 Upgrade plan (only with `--fix-plan`)

Ordered steps, each labeled **[safe to auto-apply]** or **[needs testing]**:

1. **Security fixes first.** Group compatible fixes into a single step per
   ecosystem (e.g. one `npm install pkg@x.y.z ...` command covering all
   patch/minor security bumps). Patch/minor security fixes → safe to
   auto-apply; major security fixes → needs testing.
2. **Safe minors and patches** (non-security) — grouped per ecosystem.
3. **Majors** — one step each, with a **one-line breaking-change note**.
   Check the package's changelog/release notes via WebFetch **only for
   majors that fix vulnerabilities**; for other majors, note the version
   jump and advise checking the changelog before upgrading.

For every step include the exact command the user would run — but do not run
it. End the plan by reminding the user that nothing has been applied.
