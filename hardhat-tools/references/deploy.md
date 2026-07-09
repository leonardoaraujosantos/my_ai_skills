# Deployment & Verification (Ignition + scripts)

> ⚠️ **Safety gate (from `SKILL.md`).** Deploying to or sending transactions on any **non-local** network — `ignition deploy --network <live>`, `hardhat run scripts/deploy.js --network <live>`, live `hardhat verify` — requires explicit user approval **in the conversation**. Everything below is written to rehearse on the local Hardhat Network / a fork first and touch a real network only last, after a green simulation and a yes.

## Ignition — the declarative deployment system

Ignition (`@nomicfoundation/hardhat-ignition`; bundled in HH3, a plugin in HH2) describes *what* to deploy as a module; it plans, batches, sends, and records the deployment so re-runs are idempotent and resumable.

### Module (`ignition/modules/Vault.ts`)

```ts
import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

export default buildModule("VaultModule", (m) => {
  const owner = m.getParameter("owner", "0x0000000000000000000000000000000000000001");
  const vault = m.contract("Vault", [owner]);          // constructor args
  m.call(vault, "initialize", []);                      // post-deploy call
  return { vault };
});
```

### Deploy — escalate from local to live

```bash
# 1. Ephemeral in-memory network — no flag needed (ALWAYS ALLOWED). Verifies the module executes.
npx hardhat ignition deploy ignition/modules/Vault.ts

# 2. Local persistent node (ALLOWED). Terminal A: npx hardhat node
npx hardhat ignition deploy ignition/modules/Vault.ts --network localhost

# 3. Mainnet fork (ALLOWED) — realistic state, still local.
#    (point a network at forking.url, then --network <that>)

# 4. LIVE NETWORK — GATED. Only after approval:
npx hardhat ignition deploy ignition/modules/Vault.ts --network sepolia \
  --parameters ignition/params.json
```

Deployment state is written under `ignition/deployments/<chainId-or-id>/`. Manage it:

```bash
npx hardhat ignition deployments              # list deployment ids
npx hardhat ignition status <deploymentId>    # what executed / is pending
npx hardhat ignition visualize ignition/modules/Vault.ts   # HTML plan report
npx hardhat ignition wipe <deploymentId> <futureId>        # reset to re-run a step
npx hardhat ignition verify <deploymentId>    # verify all deployed contracts (GATED)
```

Because Ignition is resumable, a deploy interrupted mid-way (e.g., a failed tx) can be re-run and it continues from where it stopped rather than redeploying everything.

## Script-based deploy (Hardhat 2 style, still valid)

```js
// scripts/deploy.js
const { ethers } = require("hardhat");
async function main() {
  const vault = await ethers.deployContract("Vault", [ownerAddress]);
  await vault.waitForDeployment();
  console.log("Vault:", await vault.getAddress());
}
main().catch((e) => { console.error(e); process.exit(1); });
```

```bash
npx hardhat run scripts/deploy.js                      # in-memory (allowed)
npx hardhat run scripts/deploy.js --network localhost  # local node (allowed)
npx hardhat run scripts/deploy.js --network sepolia    # GATED — approval required
```

## Signing keys

- **Hardhat 3:** store the deployer key in the encrypted keystore (`npx hardhat keystore set DEPLOYER_KEY`) and reference it with `configVariable("DEPLOYER_KEY")`. Never inline it.
- **Hardhat 2:** read from `.env` (`accounts: [process.env.DEPLOYER_KEY]`), gitignored. For real funds prefer a hardware wallet plugin over a hot key.
- Never echo a private key, never put one on a command line, never commit one. Rotate any key that touches a shared shell.

## Verification (publishes source — confirm first)

```bash
# Standalone verify of an already-deployed contract (GATED: publishes source to the explorer):
npx hardhat verify --network sepolia 0xADDR "constructorArg1" 42
```

Configure the explorer key under `etherscan.apiKey` (HH2) or the `hardhat-verify` plugin config (HH3, which also supports Blockscout and Sourcify targets: `hardhat verify etherscan|blockscout|sourcify`). Match the compiler version and optimizer settings in config to what was deployed, or verification mismatches.

## Pre-deploy checklist

Before requesting approval to deploy to a live network, confirm:

- [ ] `npx hardhat test` green (and Solidity tests via `hardhat test solidity` on HH3)
- [ ] Ignition module runs clean on the **in-memory network** and on a **fork**
- [ ] `hardhat ignition visualize` reviewed — the plan deploys exactly what's intended
- [ ] Constructor args and owner/admin addresses double-checked (not a dev/local address)
- [ ] Compiler version + optimizer settings pinned in config and matched for verification
- [ ] Slither run and findings triaged (`references/security.md`)
- [ ] The exact `--network <live>` command shown to the user and explicitly approved
