# Running a Dev Chain and `config.yml`

v29 spelling (`ignite chain …`); on v30 use `ignite cosmos chain …`. Everything here is for **local development**. Ignite's help: "The serve command is meant to be used ONLY FOR DEVELOPMENT PURPOSES … For production, you may want to run `appd start` manually."

## `chain serve`

Build the binary, init a one-validator data dir, start the node, watch the source tree, rebuild/re-init/restart on change (keeping state by exporting/importing genesis where it can).

```bash
ignite chain serve                     # default ./config.yml
ignite chain serve --reset-once        # wipe state once at start (-r)
ignite chain serve --force-reset       # wipe state on start and on every change (-f)
ignite chain serve -c mars.yml         # second chain from the same source (e.g. IBC testing); give it different ports/home
ignite chain serve --home ./.devhome   # data dir (default $HOME/.<project>)
ignite chain serve -o serve.log        # no TUI, log to file, implies --yes (good for agents and CI)
ignite chain serve --skip-proto --skip-build --quit-on-fail --generate-clients --build.tags <tags>
```

On start (observed, v29.10.1) it prints the Tendermint RPC, the API, the faucet URL, the data directory, and the app binary path (`$(go env GOPATH)/bin/<app>d`). It also prints **every account's mnemonic** while "Initializing accounts…". The `-o` log file therefore contains mnemonics: keep it out of git and shared logs.

Default ports are the Cosmos SDK / CometBFT ones (RPC 26657, P2P 26656, API 1317, gRPC 9090) plus the faucet on 4500. If another node already listens there (a second chain, a docker devnet), the second chain cannot bind them. Move every port through `validators[0].app` / `.config` (below) instead of stopping the other node.

## `chain build` and `chain init`

```bash
ignite chain build                          # proto gen + go mod + build, installs to $(go env GOPATH)/bin
ignite chain build -o dist                  # binary into ./dist instead (verified)
ignite chain build --release -t linux:amd64 -t darwin:arm64 [--release.prefix mychain]   # tarballs in ./release/
ignite chain build --check-dependencies     # go mod verify first
ignite chain build --debug                  # debug binary
ignite chain init [--home DIR]              # build + init data dir + genesis accounts + gentx, but do not start
```

`init` runs the equivalent of `appd init`, `add-genesis-account`, `gentx`, `collect-gentxs`. Use it to inspect the generated `genesis.json`, `app.toml`, `config.toml`, `client.toml` before deciding what to pin in `config.yml`.

Other `chain` subcommands from `--help` (not exercised): `faucet [address] [coins]`, `simulate`, `debug`, `lint` (golangci-lint), `modules`.

## Faucet

`config.yml`'s `faucet.name` account hands out `faucet.coins` per request. Verified on 2026-10-08:

```bash
curl -X POST http://127.0.0.1:4500 -d '{"address":"cosmos1..."}'     # -> {"hash":"..."}
ignite chain faucet cosmos1... 5token                                 # CLI route
```

It listens on all interfaces (`0.0.0.0`), so other hosts on the network can draw from it while `serve` runs.

## `config.yml` reference

Source: https://docs.ignite.com (Configuration → config.yml) plus the file `scaffold chain` generates. Default from v29.10.1:

```yaml
version: 1
validation: sovereign          # or consumer (Interchain Security consumer chain)
default_denom: stake
accounts:
- name: alice
  coins: [20000token, 200000000stake]
- name: bob
  coins: [10000token, 100000000stake]
client:
  openapi:
    path: docs/static/openapi.json
faucet:
  name: bob
  coins: [5token, 100000stake]
validators:
- name: alice
  bonded: 100000000stake
- name: validator1             # present in the template; docs say only the FIRST validator is started
  bonded: 200000000stake
- name: validator2
  bonded: 100000000stake
```

Keys and what they do:

| Key | Meaning |
|---|---|
| `accounts[].name`, `coins` | Genesis accounts and balances; the keyring name you pass to `--from`. Every denom listed here exists at genesis. |
| `accounts[].mnemonic` | Derive the key from this mnemonic instead of a fresh random one. Anything here is committed: **dev-only phrases**. |
| `accounts[].address` | Fund an address without creating a key (you cannot sign from it). Not allowed together with `mnemonic`, and not for validator accounts. |
| `accounts[].cointype` | BIP-44 coin type for this key. |
| `validators[].name`, `bonded` | Account that self-delegates; `bonded` must be ≥ 1000000 and ≤ that account's balance. |
| `validators[].home` | Data dir (default `$HOME/.<project>`). |
| `validators[].app` / `.config` / `.client` | Persistent overrides for `app.toml` / `config.toml` / `client.toml` (these files are rewritten on reset). |
| `genesis:` | Deep-merged into the generated `genesis.json` (`chain_id`, any `app_state.<module>…`). Persists across `init`/`serve`. |
| `build.main`, `build.binary`, `build.ldflags`, `build.proto.path` | Main package path, binary name, linker flags, proto dir. |
| `faucet.name`, `coins`, `coins_max`, `rate_limit_window`, `port` | Faucet account, per-request amount, per-address cap, cap window (seconds), port (4500). |
| `client.openapi.path`, `typescript.path`, `composables.path`, `hooks.path` | Output paths for `ignite generate`. |
| `include:` | Merge other local or remote YAML files into this config. |

Example: move every port and pin genesis values (the port block is the one used for the 2026-10-08 verification run, which ran next to another node on the default ports):

```yaml
validators:
- name: alice
  bonded: 100000000stake
  home: ./.devhome
  app:
    api:  { address: tcp://127.0.0.1:51317 }
    grpc: { address: 127.0.0.1:59090 }
    minimum-gas-prices: 0.025stake
  config:
    rpc:   { laddr: tcp://127.0.0.1:56657, pprof_laddr: 127.0.0.1:56060 }
    p2p:   { laddr: tcp://127.0.0.1:56656 }
    proxy_app: tcp://127.0.0.1:56658
    consensus: { timeout_commit: 5s }
faucet:
  name: bob
  coins: [5token, 100000stake]
  port: 54500
genesis:
  chain_id: mychain-local-1
  app_state:
    staking:
      params: { bond_denom: uacme }    # then give the validator account uacme to bond
```

### What `config.yml` is not

- **Not a production genesis.** Balances, bonded stake, and module params here exist so one laptop validator can start. A real launch needs its own genesis process (gentx collection from independent validators, audited allocations, real denoms and params).
- **Not a key store.** Generated mnemonics rotate on every reset and are printed to the console; pinned ones are in git. Neither may hold value anywhere but localhost.
- **Not multi-validator.** The docs state only the first `validators` entry is started; use `ignite testnet multi-node` (help: "Initialize and provide multi-node on/off functionality", not exercised) or real infrastructure for more.

Real-world shape: a chain that grew past the template keeps `config.yml` mainly for its dev `genesis:` block, e.g. a custom `default_denom`, `bank.denom_metadata`, and EVM / fee-market params under `app_state`, with `build.main` pointing at its own `cmd/<app>d`.
