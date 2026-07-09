# Hardhat 2 (CommonJS, the installed base)

Most existing projects and tutorials are Hardhat 2: CommonJS config, Mocha/Chai, `ethers` from the Hardhat Runtime Environment (HRE), and the classic plugin ecosystem. Runs on Node 18/20/22. Verified against Hardhat 2.28.6.

## Project shape

```
package.json          # no "type": "module" (CommonJS)
hardhat.config.js
contracts/
test/                 # *.js / *.ts, Mocha
scripts/              # deploy.js etc.
```

## Config (`hardhat.config.js`)

```js
require("@nomicfoundation/hardhat-toolbox");   // must be the @hh2 tag — see below
require("dotenv").config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.28",
    settings: { optimizer: { enabled: true, runs: 200 } },
  },
  networks: {
    hardhat: {
      // forking: { url: process.env.MAINNET_RPC_URL, blockNumber: 19000000 },
    },
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "",
      accounts: process.env.DEPLOYER_KEY ? [process.env.DEPLOYER_KEY] : [],
    },
  },
  etherscan: { apiKey: process.env.ETHERSCAN_API_KEY },
};
```

> ⚠️ **Toolbox tag.** In an HH2 project the toolbox must be the **`hh2`** tag:
> `npm i -D "@nomicfoundation/hardhat-toolbox@hh2"`.
> Installing plain `@nomicfoundation/hardhat-toolbox` (now HH3-only) fails at load with a "please install the `hh2` tag" error.

> ⚠️ **Secrets.** `accounts: [process.env.DEPLOYER_KEY]` reads a **plaintext** key from the environment. Keep it in `.env` (gitignored), never committed, and prefer a hardware wallet or the HH3 keystore for anything holding real funds.

## Build, test, tasks

```bash
npx hardhat compile
npx hardhat clean
npx hardhat test                 # Mocha
npx hardhat test test/Vault.js   # one file
npx hardhat console --network sepolia
npx hardhat node                 # local JSON-RPC, chain id 31337
npx hardhat flatten contracts/Vault.sol > flat.sol
```

The `hardhat-toolbox@hh2` bundle also exposes:

```bash
npx hardhat coverage             # solidity-coverage report
REPORT_GAS=true npx hardhat test # hardhat-gas-reporter table (config-driven)
npx hardhat verify --network sepolia 0xADDR "constructorArg1"   # GATED: publishes source
```

## Testing pattern

`ethers` comes from the HRE (`require("hardhat")`), Mocha describes, `chai` matchers from `@nomicfoundation/hardhat-chai-matchers`:

```js
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");

describe("Vault", function () {
  async function deploy() {
    const [owner, alice] = await ethers.getSigners();
    const vault = await ethers.deployContract("Vault");
    return { vault, owner, alice };
  }

  it("deposits", async function () {
    const { vault, alice } = await loadFixture(deploy);
    await vault.connect(alice).deposit({ value: 1_000n });
    expect(await vault.balanceOf(alice.address)).to.equal(1_000n);
  });

  it("reverts on overdraw", async function () {
    const { vault, alice } = await loadFixture(deploy);
    await expect(vault.connect(alice).withdraw(1n)).to.be.revertedWith("insufficient");
  });
});
```

`loadFixture` (from `@nomicfoundation/hardhat-network-helpers`) snapshots state so each test restarts from the fixture cheaply. Other helpers: `time.increase`, `time.increaseTo`, `mine`, `setBalance`, `impersonateAccount`, `takeSnapshot`.

## Mainnet forking

Uncomment the `forking` block in the `hardhat` network (config above), or per-run:

```bash
npx hardhat test --network hardhat   # with forking.url set
```

or fork from a standalone node:

```bash
npx hardhat node --fork "$MAINNET_RPC_URL" --fork-block-number 19000000
```

Forked results are realistic and local — no real transactions. Pin `blockNumber` for deterministic, cacheable tests.

## Deployment

Script-based (`scripts/deploy.js` + `hardhat run`) or Ignition (`@nomicfoundation/hardhat-ignition`) — see `references/deploy.md`. Any deploy/verify to a live network is gated (see `SKILL.md`).

## Common failure → fix

| Symptom | Cause / fix |
|---------|-------------|
| "please install the `hh2` tag" on config load | Toolbox is the HH3 build; `npm i -D @nomicfoundation/hardhat-toolbox@hh2` |
| `HH8` invalid config / ESM errors | HH2 config is CommonJS — don't add `"type":"module"`; use `.cjs` if the package is ESM |
| `revertedWith` matcher missing | Ensure `@nomicfoundation/hardhat-chai-matchers` loaded (bundled by the toolbox) |
| Fork tests slow/flaky | Pin `forking.blockNumber`; results cache under the project's cache dir |
| Gas report empty | `hardhat-gas-reporter` is config-driven; enable it and/or set `REPORT_GAS=true` |
