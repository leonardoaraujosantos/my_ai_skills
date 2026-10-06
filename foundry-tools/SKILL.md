---
name: foundry-tools
description: Solidity smart-contract development, testing, and security workflows with Foundry (forge, cast, anvil, chisel) plus Slither static analysis. Covers building and testing (unit, fuzz, invariant, fork), gas profiling and snapshots, coverage, chain interaction with cast, local anvil nodes, keystore-based signing, static analysis, and a checks-effects-interactions / reentrancy / access-control review checklist. Deploys and transactions are gated behind explicit approval. Use when the user says "run forge test", "test this contract", "fuzz/invariant test", "gas report", "forge coverage", "slither this", "audit this contract", "cast call/send", "fork mainnet", "deploy this contract", "verify on etherscan", or "why does this revert".
argument-hint: [test|deploy|cast|security] [contract or topic]
---

# Foundry Tools — Solidity Development, Testing & Security

Playbooks for the Foundry toolchain (`forge`, `cast`, `anvil`, `chisel`) and Slither, oriented around this repo's rule that **Solidity is security-critical by default**: checks-effects-interactions, reentrancy/access-control review, a pinned pragma, and Foundry tests for every change.

| Task | Reference file |
|------|----------------|
| Build, unit/fuzz/invariant/fork tests, gas, coverage, debugging | `references/testing.md` |
| Chain interaction, encoding/decoding, storage, tx tracing | `references/cast.md` |
| Deploy scripts, broadcast, verify, anvil, keystores | `references/deployment.md` |
| Static analysis + manual security review checklist | `references/security.md` |

**How to use this skill:** identify the task, read the matching reference file(s) before answering, and run commands against the user's Foundry project. For any change to contract logic, default to writing/extending a test and re-running `forge test`. For anything that reviews security, read `references/security.md` and apply the checklist — do not just run Slither and stop.

## ⚠️ Safety gate — never sign, send, or deploy without explicit approval

This repo's global rule: **NEVER deploy a contract or sign/send a transaction without explicit approval.** In Foundry terms, the following are **blocked by default** and require the user to confirm *in this conversation* first:

- `forge script ... --broadcast` (deploys / sends the scripted transactions)
- `forge create` (deploys a contract)
- `cast send`, `cast publish` (send a signed transaction / publish a raw tx)
- any `cast wallet sign` / signing of a message or transaction
- `forge verify-contract` against a live explorer (low risk, but confirm — it publishes source)

Default instead to **read-only / simulated** equivalents, which are always allowed:

- `forge script` **without** `--broadcast` = a dry run (simulates, prints the trace, writes nothing on-chain)
- `cast call`, `cast estimate`, `cast run <txhash>` = read/simulate, never send
- a local **anvil** node or `--fork-url` fork = a throwaway sandbox; broadcasting *there* is fine and is the right way to rehearse a deploy

When a deploy or send is genuinely wanted: rehearse it on anvil/fork first, show the user the simulation output and the exact command, and only run the broadcasting version after they say yes. Never put a raw private key on the command line — use a keystore `--account` (see `references/deployment.md`).

## Quick start

```bash
# Build + test (add -vvv for traces, -vvvv for full call/stack traces on failure)
forge build
forge test
forge test --match-test testWithdraw -vvv
forge test --match-contract VaultTest

# Fuzz runs are default for functions taking arguments; invariants run invariant_* functions.
forge test --gas-report          # per-function gas table
forge snapshot                   # write .gas-snapshot; diff shows gas deltas vs a change
forge coverage                   # line/branch/function coverage table
forge fmt                        # format; `forge fmt --check` in CI

# Fork a live network into a local test (needs an RPC URL)
forge test --fork-url "$ETH_RPC_URL" --match-contract ForkTest

# Static analysis (Slither understands Foundry projects natively)
slither .

# Local sandbox chain
anvil                            # 10 funded dev accounts, chain id 31337
cast block-number --rpc-url http://localhost:8545
```

## Routing table

| The user asks… | Go to |
|----------------|-------|
| "run/write tests", "fuzz", "invariant", "coverage", "gas", "why does it revert" | `references/testing.md` |
| "call this function", "read storage slot", "decode this calldata", "trace this tx", "what's the balance" | `references/cast.md` |
| "deploy", "broadcast", "verify on etherscan", "spin up anvil", "manage a signing key" | `references/deployment.md` (mind the safety gate) |
| "audit", "slither", "is this safe", "check for reentrancy", "review this contract" | `references/security.md` |

## Environment notes

- Verified against Foundry 1.7.x, Slither 0.11.x, solc 0.8.x.
- Install Foundry with `foundryup` (from `curl -L https://foundry.paradigm.xyz | bash`); Slither with `pip install slither-analyzer` (needs a solc it can select via `solc-select` or an in-project `foundry.toml` `solc` pin).
- Config lives in `foundry.toml`; dependencies are git submodules under `lib/` managed by `forge install` / `forge update` (or `soldeer` if the project uses it).
- Secrets (RPC URLs, explorer API keys) belong in `.env` loaded by the shell or in `foundry.toml` `[rpc_endpoints]` / `[etherscan]`, never hardcoded in scripts.
