# Global Rules

## Git Commits & PRs

- Never mention Claude or AI in commit messages or PRs (no "Co-Authored-By: Claude")
- Write commit messages as the developer would: concise, technical, what changed and why
- Every PR needs a descriptive body
- Every bug fix needs a regression test in the same PR
- PRs must update the project documentation (or openspec) when behavior changes

## Code Style

- Use OpenSpec (skill + CLI) for medium/large features, and for any change touching auth, billing, security, or data models, in repos that have an `openspec/` directory
- Keep per-function cognitive complexity within the domain targets in the cognitive-complexity skill (frontend 8–12, backend 15, compilers/parsers 25–35); measure with that skill and flag genuinely irreducible functions instead of mangling them
- Easy-to-maintain code is an explicit objective: clean, readable, simple to extend, and maintainable by both humans and agents — prefer the simpler design when in doubt

## Languages

Primary: Python, TypeScript/JavaScript, Go, C++20, Solidity, SystemVerilog.

- Default to Python for scripts/tooling; prefer TypeScript over JavaScript for new code; target C++20
- Solidity is security-critical by default: checks-effects-interactions, reentrancy/access-control review, pinned pragma, Foundry/Hardhat tests for every change — NEVER deploy a contract or sign/send a transaction without explicit approval
- SystemVerilog: distinguish synthesizable RTL from testbenches; blocking vs non-blocking discipline; an RTL change isn't done until simulated (verilator/iverilog) — never claim hardware behavior from code reading alone

## Verification

- Before claiming an issue is pre-existing, verify it on the main branch first
- Diff linter/type-check/test results against main before stating errors are not yours

## Communication

- Be concise and direct; no filler
