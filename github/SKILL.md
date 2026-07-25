---
name: github
description: Resilient GitHub access (issues, PRs, REST API) that survives local network blocks of api.github.com. Use when `gh` commands hang/time out, when fetching or editing issues/PRs over the API, or to diagnose whether GitHub is actually down vs blocked locally. Triggers — "gh hangs", "github times out", "can't reach github api", "is github down", view/edit issue or PR.
---

# GitHub (resilient)

`gh` and the GitHub REST API can hang on some networks because DNS hands out a
GitHub **Azure edge IP** for `api.github.com` (e.g. `4.228.31.149`) that is
black-holed locally, while the classic anycast IPs (`140.82.x.x`) still work.
`gh` offers no per-call IP override, so its API calls time out — even though
`git push` over SSH and `github.com` (web) keep working.

This skill wraps GitHub access through `ghx.sh`, which auto-detects the block,
falls back to `curl --resolve` against a known-good IP, and checks
githubstatus.com to tell a **real outage** apart from a **local block**.

## When `gh` times out — do this first

```bash
~/.claude/skills/github/ghx.sh doctor
```

It prints, in order: GitHub's published status, whether `api.github.com` is
reachable directly, and (if not) which fallback IP works. It tells you whether
the problem is GitHub (wait it out) or your network (use the fallback).

## Reading/writing the API (works regardless of the block)

Use `ghx api`, which mirrors `gh api` paths. It tries a direct call first and
only falls back to `curl --resolve` when needed — so it's safe to use always.

```bash
GHX=~/.claude/skills/github/ghx.sh

# Read an issue / PR
$GHX api repos/OWNER/REPO/issues/191
$GHX api repos/OWNER/REPO/pulls/281

# List, comment, create (POST/PATCH with a JSON body)
$GHX api repos/OWNER/REPO/issues?state=open
$GHX api repos/OWNER/REPO/issues/191/comments -X POST -d '{"body":"done"}'
$GHX api repos/OWNER/REPO/issues/191 -X PATCH -d '{"state":"closed"}'
```

Pipe through `python3 -c '...'` or `jq` to extract fields. The token is read
automatically from `gh auth token` (falls back to `$GITHUB_TOKEN`/`$GH_TOKEN`).

## When you really need the `gh` binary (e.g. `gh pr create`)

`ghx run <gh args>` runs real `gh` if the API is reachable; otherwise it tells
you the one-time permanent fix — pin `api.github.com` to a working IP:

```bash
echo "140.82.112.6  api.github.com" | sudo tee -a /etc/hosts
```

After that, `gh` (and everything else) works normally. Remove the line when the
network's routing to the Azure IP recovers:

```bash
sudo sed -i '' '/140\.82\.112\.6  api\.github\.com/d' /etc/hosts
```

## Just checking if GitHub is down

```bash
~/.claude/skills/github/ghx.sh status   # queries githubstatus.com
```

## Notes
- The fallback IP list and timeout are overridable via `GHX_API_IPS` and
  `GHX_TIMEOUT`.
- This does **not** affect git over SSH (which is unaffected by the block) —
  use normal `git push`/`git pull` as usual.
- For repo-aware convenience inside this project, the default repo is
  `leonardoaraujosantos/matlab_llvm`.
