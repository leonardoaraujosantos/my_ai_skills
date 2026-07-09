# Hardhat 3 (ESM, TypeScript-first)

Hardhat 3 is a rewrite: ESM, TypeScript config with a `plugins` array, a network **manager** (multiple connections per run), a built-in encrypted **keystore**, and three test runners — `node:test`, Mocha, and **Solidity tests** (Foundry-style `.t.sol`). Requires **Node ≥ 22.13.0**. Verified against Hardhat 3.9.1.

## Project shape

```
package.json          # "type": "module"
hardhat.config.ts
contracts/
test/                 # *.ts (node:test or Mocha) and/or *.t.sol (Solidity tests)
ignition/modules/     # deployment modules
```

`package.json` must have `"type": "module"`.

## Config (`hardhat.config.ts`)

```ts
import type { HardhatUserConfig } from "hardhat/config";
import hardhatToolboxMochaEthers from "@nomicfoundation/hardhat-toolbox-mocha-ethers";
// or: import hardhatToolboxViem from "@nomicfoundation/hardhat-toolbox-viem";

const config: HardhatUserConfig = {
  plugins: [hardhatToolboxMochaEthers],
  solidity: {
    version: "0.8.28",
    settings: { optimizer: { enabled: true, runs: 200 } },
  },
  networks: {
    sepolia: {
      type: "http",                       // HH3 networks declare a `type`
      url: configVariable("SEPOLIA_RPC_URL"),
      accounts: [configVariable("DEPLOYER_KEY")],   // resolved from keystore/env, not plaintext
    },
  },
};

export default config;
```

`configVariable("NAME")` defers the value to the encrypted keystore or an env var — **never inline a private key or RPC secret**. The two official toolboxes bundle the common plugins; pick `-mocha-ethers` (ethers + Mocha, familiar to HH2 users) or `-viem` (viem, HH3's default direction).

## Build & compile

```bash
npx hardhat build            # compile (canonical HH3 name)
npx hardhat compile          # alias of build
npx hardhat clean            # wipe cache + artifacts
npx hardhat flatten contracts/Vault.sol
```

## Testing

HH3 has three runners under one `test` task:

```bash
npx hardhat test             # run all suites (Solidity + JS)
npx hardhat test solidity    # only Solidity .t.sol tests (Foundry-style)
npx hardhat test mocha       # only the JS/TS Mocha (or node:test) suite
npx hardhat test test/Vault.ts   # a single file
```

### JS/TS test — get a network connection

In HH3 you obtain ethers/viem from a **network connection**, not a global import. `network.connect()` is deprecated in 3.9; use `getOrCreate` / `create`:

```ts
import { expect } from "chai";
import { network } from "hardhat";

describe("Vault", function () {
  it("deposits and reverts on overdraw", async function () {
    const { ethers } = await network.getOrCreate("default");   // or network.create()
    const vault = await ethers.deployContract("Vault");
    await vault.deposit({ value: 1_000n });
    expect(await vault.balanceOf((await ethers.getSigners())[0])).to.equal(1_000n);
    await expect(vault.withdraw(9_999n)).to.be.revertedWith("insufficient");
  });
});
```

With the **viem** toolbox the connection yields `viem` instead of `ethers`:

```ts
const { viem } = await network.getOrCreate("default");
const vault = await viem.deployContract("Vault");
```

`chai` matchers from `hardhat-chai-matchers` (`revertedWith`, `revertedWithCustomError`, `emit`, `changeEtherBalance`) are bundled by the toolboxes.

### Solidity tests (`*.t.sol`)

HH3 runs Foundry-style Solidity tests natively. Write `test/Vault.t.sol` importing `forge-std`-style helpers and run `npx hardhat test solidity`. This lets a Hardhat project keep fast, in-EVM unit tests alongside its JS integration tests — the same discipline as `foundry-tools/references/testing.md`.

## Local node & forking

```bash
npx hardhat node                         # local JSON-RPC, chain id 31337
```

Mainnet forking is configured on a simulated network (HH3 uses an `edr-simulated` network type with a `forking` block); the exact keys are version-sensitive — confirm against the installed version's docs, then run tests/deploys against that network. A fork gives realistic on-chain state locally with no real transactions, making it the correct place to rehearse.

## Gas & coverage

The toolbox includes gas reporting and coverage integration; exact task/flag names shift across 3.x, so discover them on the project:

```bash
npx hardhat 2>&1 | grep -iE "coverage|gas"   # list what the installed toolbox exposes
npx hardhat test                              # gas reporting is typically emitted here when enabled in config
```

Enable gas reporting in `hardhat.config.ts` (reporter options) rather than assuming a flag. For a hard CI gate on gas, prefer the Foundry `forge snapshot --check` path if the project has the `hardhat-foundry` integration.

## Keystore (built-in, encrypted)

HH3 ships a first-class secret store — use it for RPC URLs, explorer keys, and deployer keys instead of `.env` in the clear:

```bash
npx hardhat keystore set SEPOLIA_RPC_URL     # prompts for the value + a password
npx hardhat keystore set DEPLOYER_KEY
npx hardhat keystore list
npx hardhat keystore get SEPOLIA_RPC_URL
npx hardhat keystore delete DEPLOYER_KEY
```

Reference stored values in config via `configVariable("SEPOLIA_RPC_URL")`.

## Deployment

Ignition is the HH3 deployment system — see `references/deploy.md`. Deploys to a live network are gated (see `SKILL.md`).

## Migrating from Hardhat 2

- `hardhat.config.js` (CommonJS, `require`) → `hardhat.config.ts` (ESM, `plugins: []`, `import`).
- `package.json` gains `"type": "module"`.
- Global `require("hardhat").ethers` → `await network.getOrCreate(...)` then destructure `ethers`/`viem`.
- Networks gain a `type` field (`"http"` / simulated).
- Plaintext `accounts: [process.env.KEY]` → `configVariable(...)` backed by the keystore.
- `scripts/deploy.js` + `hardhat run` → Ignition modules (the script path still works if you prefer it).
- Node must be ≥ 22.13.0.
