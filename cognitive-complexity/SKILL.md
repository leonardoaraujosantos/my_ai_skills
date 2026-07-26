---
name: cognitive-complexity
description: Measure Cognitive Complexity (SonarSource metric — how hard code is for a human to read) of a folder of C/C++, Python, Go, TypeScript/JavaScript, Solidity, or SystemVerilog code. Reports a ranked, banded list of the most complex functions so you can target refactors. Uses installed open-source analyzers (complexipy, gocognit, eslint-plugin-sonarjs, clang-tidy, solhint, scc) — it does not re-implement the metric, and clearly labels languages where only cyclomatic (Solidity) or a per-file estimate (SystemVerilog) is available. Triggers — "cognitive complexity", "how complex is this code", "which functions need refactoring", "complexity report", "smart contract complexity", "solidity complexity", "RTL/SystemVerilog complexity".
argument-hint: [path ...] [--top N] [--threshold N] [--lang python,go,ts,c,cpp,solidity,sv] [--json]
allowed-tools: Bash(python3:*), Bash(bash:*), Bash(node:*), Bash(complexipy:*), Bash(gocognit:*), Bash(clang-tidy:*), Bash(lizard:*), Bash(solhint:*), Bash(scc:*), Read, Glob, Grep
---

# Cognitive Complexity

Cognitive Complexity (SonarSource, 2016) measures how hard code is for a **human** to read and reason about — distinct from Cyclomatic Complexity, which measures how many paths you must *test*. It penalizes things that break linear reading: each flow break (`if`, `else`, loop, `catch`, `&&`/`||`, ternary, recursion) adds +1, and **nesting compounds** the penalty (an `if` two levels deep costs more than one at the top). Shorthands like a `switch` block count as 1. Lower is more maintainable.

This skill does **not** compute the metric itself — it dispatches each file to the established open-source analyzer for its language and normalizes the output into one ranked report.

| Language | Analyzer | Metric |
|----------|----------|--------|
| Python | [`complexipy`](https://github.com/rohaquinlop/complexipy) | cognitive |
| Go | [`gocognit`](https://github.com/uudashr/gocognit) | cognitive |
| TS / JS | `eslint` + [`eslint-plugin-sonarjs`](https://github.com/SonarSource/eslint-plugin-sonarjs) | cognitive (SonarSource's own) |
| C / C++ | `clang-tidy` `readability-function-cognitive-complexity` | cognitive |
| C / C++ *(fallback)* | [`lizard`](https://github.com/terryyin/lizard) | **cyclomatic** (labeled) |
| Solidity | [`solhint`](https://github.com/protofire/solhint) `code-complexity` rule | **cyclomatic** (labeled; per function, but functions scoring exactly 1 are not emitted by solhint) |
| SystemVerilog (.sv/.svh) | [`scc`](https://github.com/boyter/scc) | **cyclomatic-style estimate, per FILE** (labeled; see limitation below) |

**SystemVerilog limitation (verified, honest):** no open-source tool reports per-function/per-always-block complexity for SV. `verible-verilog-lint` has **no** complexity, nesting-depth, or statement-count rule (its full ruleset is structural/style lint: `always-comb`, `case-missing-default`, `explicit-begin`, `line-length`, naming rules, …); `svlint` is style-only; `lizard` does not support Verilog. The best real numeric signal is `scc`'s per-file branch-count estimate — useful for ranking *files*, not functions. Treat SV scores as a coarse proxy.

## Bands (per SonarSource / common linting practice)

| Score | Band | Meaning |
|-------|------|---------|
| 0–10 | 🟢 Excellent | Reads like a book |
| 11–15 | 🟡 Acceptable | Maintainable, worth a sanity check |
| 16–25 | 🟠 Warning | Refactor strongly recommended |
| 26+ | 🔴 Critical | Significant tech debt, bug-prone |

## Per-domain targets (max per function)

Acceptable complexity depends on the domain — judge results against these targets, not the generic bands alone:

| Domain | Max per function | Notes |
|--------|------------------|-------|
| Frontend (components, hooks, UI state) | 8–12 | Extract custom hooks; use `.map`/`.filter`; keep presentation and algorithm separate |
| Backend services (APIs, business logic) | 15 | SonarQube default; guard clauses, push rules into service/use-case classes |
| Compilers / parsers / systems | 25–35+ | AST traversal, recursion, large pattern matches; isolate with the Visitor pattern and document; still split above ~35 |
| Solidity (smart contracts) | 10–15 | Security-critical code should stay simple — complex control flow hides reentrancy/accounting bugs and inflates gas; metric here is **cyclomatic** (solhint), slightly stricter than the cognitive bands |
| SystemVerilog / RTL | n/a (per-file estimate only) | No per-function metric exists in open-source tooling; scc's per-file number ranks hot files. Rule of thumb: keep a file's estimate under ~30 and split big `always` blocks / deep `case`-in-`case` nesting regardless of the number |

These are guidance, not hard gates — a genuinely irreducible algorithm may exceed them; flag it rather than mangling the code to satisfy a number.

## Usage

```bash
SKILL=~/.claude/skills/cognitive-complexity
python3 $SKILL/scripts/cogcom.py <path> [<path> ...] [options]
```

Options:
- `--top N` — how many worst functions to list (default 15)
- `--threshold N` — only list functions scoring ≥ N (default 0; the distribution always covers all)
- `--lang python,go,ts,c,cpp,solidity,sv` — restrict to specific languages (`systemverilog` and `sol` are accepted aliases)
- `--lizard` — force `lizard` (cyclomatic) for C/C++ even if `clang-tidy` is present
- `--json` — machine-readable output (`{records:[{file,function,line,score,language,metric}], warnings}`)

The walker skips `node_modules`, `vendor`, `dist`, `build`, `__pycache__`, `.venv`, dotfolders, etc.

### Examples

```bash
# Whole repo, default report
python3 $SKILL/scripts/cogcom.py ./src

# Only the worst offenders that warrant a refactor
python3 $SKILL/scripts/cogcom.py ./backend --threshold 16 --top 30

# Just the Python, as JSON for further processing
python3 $SKILL/scripts/cogcom.py . --lang python --json
```

## First run — install the toolchain (once)

If the report shows `... not installed (run setup.sh)` warnings, install the analyzers a single time. The skill does **not** reinstall on every call.

```bash
bash ~/.claude/skills/cognitive-complexity/scripts/setup.sh
```

This installs `complexipy`+`lizard` (pip), `gocognit` (go install), the pinned `eslint`/`sonarjs` toolchain (npm, into `scripts/ts/`), the pinned `solhint` toolchain (npm, into `scripts/solidity/`), `scc` (brew, or `go install github.com/boyter/scc/v3@latest`), and checks for `clang-tidy`. `clang-tidy` can't be auto-installed — on macOS `brew install llvm`, on Debian `apt-get install clang-tidy`. Without it, C/C++ falls back to `lizard` (cyclomatic, clearly flagged in the report).

## How to act on the results

When asked to *reduce* complexity, target the 🔴/🟠 functions and apply (in order of impact):
1. **Guard clauses / early returns** — invert conditions to handle edge cases up front instead of nesting the happy path.
2. **De-nest** — replace tracking loops with `map`/`filter`/comprehensions/`forEach`; flatten with `continue`.
3. **Extract helpers** — split a multi-purpose function into single-responsibility ones (this moves nesting penalty out of the hot function).
4. Re-run the skill to confirm the score dropped.

Caveat to relay honestly: a genuinely irreducible algorithm (heavy math, an inherently branchy state machine) may score high and that can be acceptable — flag it rather than mangling it to satisfy a number. C/C++ scored via `clang-tidy` without a compilation database may undercount functions whose bodies don't parse (missing includes); note this if coverage looks low.

## Notes for the agent

- Prefer `--json` when you need to reason over the numbers or feed a follow-up; use the default table when showing the user.
- `complexipy`'s JSON includes `refactor_plans` (a concrete reduction recipe per function) — read it via `complexipy <file> --output-format json --output <tmp>` when proposing Python refactors.
- The metric definition: <https://www.sonarsource.com/docs/CognitiveComplexity.pdf>
