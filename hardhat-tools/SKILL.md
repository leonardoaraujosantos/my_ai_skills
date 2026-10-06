---
name: hardhat-tools
description: Solidity smart-contract development, testing, and deployment with Hardhat (JS/TS toolchain). Covers both Hardhat 3 (ESM, TypeScript config, node:test + Mocha + Solidity tests, viem/ethers, network manager, built-in keystore, Ignition) and Hardhat 2 (CommonJS config, Mocha/Chai/ethers, solidity-coverage, gas reporter). Includes compiling, testing, mainnet forking, coverage and gas reporting, Ignition deployment modules, Etherscan verification, Slither on Hardhat projects, and Hardhat<->Foundry interop. Deploys and transactions are gated behind explicit approval. Use when the user says "hardhat test", "npx hardhat", "hardhat compile", "hardhat coverage", "deploy with ignition", "hardhat deploy script", "fork mainnet in hardhat", "verify on etherscan", "hardhat config", "migrate hardhat 2 to 3", or has a hardhat.config.js/ts project. For Foundry (forge/cast/anvil) use the foundry-tools skill instead.
argument-hint: [test|deploy|config|security] [contract or topic]
---

# Hardhat Tools — Solidity Development, Testing & Deployment

Playbooks for the Hardhat JS/TS toolchain, complementing `foundry-tools` (Foundry). Same repo rule applies: **Solidity is security-critical by default** — checks-effects-interactions, reentrancy/access-control review, a pinned pragma, and tests for every change.

Hardhat has two live major versions with **different config formats and test APIs**; identify which one the project uses before doing anything (see "Detect the version" below).

| Task | Reference file |
|------|----------------|
| Hardhat **3** end to end (setup, TS config, tests, forking, gas/coverage, keystore) | `references/hardhat3.md` |
| Hardhat **2** end to end (setup, JS config, Mocha/ethers, coverage, gas reporter) | `references/hardhat2.md` |
| Deployment: Ignition modules + script deploys, verification, keystores (both versions) | `references/deploy.md` |
| Static analysis on a Hardhat project + review checklist + Foundry interop | `references/security.md` |

**How to use this skill:** detect the Hardhat major version, read the matching reference file, and run commands with the project's local Hardhat (`npx hardhat …`, never a global install). For any logic change, extend a test and re-run `npx hardhat test`. For deployment or verification, read `references/deploy.md` and obey the safety gate below.

## Detect the version

```bash
# Installed major version (authoritative):
node -e "console.log(require('./node_modules/hardhat/package.json').version)"
# or from the manifest:
grep '"hardhat"' package.json
```

Quick signals: a **`hardhat.config.ts`** with a `plugins: [...]` array and `"type": "module"` in `package.json` is **Hardhat 3**; a **`hardhat.config.js`** using `require("@nomicfoundation/hardhat-toolbox")` is **Hardhat 2**. When in doubt, trust the installed version number.

## ⚠️ Safety gate — never sign, send, or deploy without explicit approval

Repo global rule: **NEVER deploy a contract or sign/send a transaction without explicit approval.** In Hardhat terms, these are **blocked by default** until the user confirms *in this conversation*:

- `npx hardhat ignition deploy … --network <live>` (deploys to a real network)
- `npx hardhat run scripts/deploy.js --network <live>` (any script that sends txs)
- any `hardhat verify` against a live explorer (low risk, but confirm — it publishes source)
- any code path that signs or broadcasts a transaction to a non-local network

Always-allowed, read-only / simulated equivalents to use instead:

- `npx hardhat test`, `npx hardhat compile`, `npx hardhat coverage` — no network side effects
- deploying to the **in-memory Hardhat Network** or a **local `npx hardhat node`** — a throwaway sandbox; deploying there is the right rehearsal
- a **mainnet fork** (local) — realistic state, no real transactions

When a live deploy is genuinely wanted: rehearse against a local node/fork, show the user the exact command and the simulated result, and run the real thing only after they say yes. Keep private keys out of config — use the HH3 keystore or `configVariable`/env vars, never a plaintext key committed in `hardhat.config`.

## Quick start

```bash
npx hardhat compile                     # build artifacts (HH3: alias of `build`)
npx hardhat test                        # run the test suite
npx hardhat test test/Vault.ts          # a single test file
npx hardhat node                        # local JSON-RPC node (chain id 31337)
npx hardhat console                     # REPL against a network

# Hardhat 3 only:
npx hardhat test solidity               # run Solidity (.t.sol) tests
npx hardhat test mocha                  # run only the Mocha/node:test suite
npx hardhat keystore set MAINNET_RPC    # store a secret in the encrypted keystore

# Hardhat 2 only (via hardhat-toolbox@hh2):
npx hardhat coverage                    # solidity-coverage report
REPORT_GAS=true npx hardhat test        # hardhat-gas-reporter table
```

## Environment / version notes (verified against HH 3.9.1 and HH 2.28.6)

- **Hardhat 3 requires Node.js ≥ 22.13.0** and is **ESM** (`"type": "module"`, TypeScript config). On older Node it aborts with a version error.
- **Toolbox packages are version-specific:** HH3 uses `@nomicfoundation/hardhat-toolbox-mocha-ethers` or `@nomicfoundation/hardhat-toolbox-viem`; HH2 needs the **`@hh2` tag** (`@nomicfoundation/hardhat-toolbox@hh2`). Installing the plain `latest` toolbox into an HH2 project fails with a "please install the hh2 tag" error.
- **`hardhat --init` needs an interactive TTY** — scaffold new projects interactively; this skill drives existing ones.
- Foundry and Hardhat coexist via `@nomicfoundation/hardhat-foundry` (see `references/security.md`).
