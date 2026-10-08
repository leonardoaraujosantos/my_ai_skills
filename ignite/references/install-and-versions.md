# Install, Versions, and Upgrading

## Install

The official installer is a [jpillora/installer](https://github.com/jpillora/installer) instance at `get.ignite.com`:

```bash
curl https://get.ignite.com/cli! | bash            # latest release, moves the binary into /usr/local/bin (needs write access)
curl https://get.ignite.com/cli | bash             # latest release, leaves ./ignite in the current directory
curl https://get.ignite.com/cli@v29.10.1 | bash    # pin a release (verified: the served script sets RELEASE="v29.10.1")
curl https://get.ignite.com/cli@v29.10.1! | bash   # pin + move to /usr/local/bin
brew install ignite                                # Homebrew (macOS/Linux), per docs.ignite.com install page
```

- `!` = move into `/usr/local/bin`; without it the binary stays in the working directory. Prefer the no-`!` form and move it yourself, or download from the releases page and check it against `ignite_<ver>_checksums.txt`.
- **"Latest" can be a release candidate.** On 2026-10-08 the unpinned installer served `RELEASE="v30.0.0-rc.2"` because GitHub marks that RC as Latest. Pin the version for anything reproducible (CI, team setup, docs).
- Upgrading: remove every old `ignite` on `PATH` first (`rm $(which ignite)` until `which ignite` is empty), then install. Stop any running `chain serve` before swapping binaries.
- Build from source: `git clone https://github.com/ignite/cli --depth=1 && cd cli && make install`.

Verify:

```bash
ignite version       # Ignite version, build date, Cosmos SDK version it scaffolds, your Go version
```

Quirk seen on 2026-10-08: the released `v29.10.1` linux/amd64 binary reports itself as `v30.0.0-rc.2-dev` in `ignite version` while its `Cosmos SDK version` line says `v0.53.6`. Trust the release you downloaded and the SDK line, not the version string.

## Go requirement

- docs.ignite.com install page (main branch, 2026-10-08): **Go 1.26.7 or higher**.
- Changelog: v29.7.0 raised the minimum to Go 1.25; v29.0.0-rc.1 moved to Go 1.24 and the `tool` directive in `go.mod`.
- Observed: `ignite scaffold chain` with **v29.10.1 + Go 1.25.2 fails** while resolving the `buf` tool dependency:
  `go: github.com/bufbuild/buf@v1.73.0 requires go >= 1.26.7 (running go 1.25.2; GOTOOLCHAIN=local+path)`.
  With Go 1.26.8 the same command succeeds and writes `go 1.26.7` into the new chain's `go.mod`. Inference: scaffolding pulls the newest `buf`, so the effective Go floor moves with buf releases, not only with Ignite releases. Install a current Go before scaffolding.

## Which Ignite scaffolds which Cosmos SDK

Source: `changelog.md` in ignite/cli (entries cited by PR number) and release notes. "Scaffolds" = the SDK version written into a newly scaffolded chain's `go.mod`.

| Ignite | Cosmos SDK scaffolded | Evidence |
|---|---|---|
| v0.24 – v0.26 | v0.46.x | v0.24.0 "Upgraded Cosmos SDK to v0.46.0 and IBC to v5"; later bumps to v0.46.7 |
| v0.27.x | v0.47.x | #3538 "bump sdk to v0.47.3 and ibc to v7.1.0" |
| v28.x | v0.50.x | v28.0.0 #3659 "cosmos-sdk v0.50.x upgrade"; v28.11.0 #4761 bumps to v0.50.14 |
| v29.x | v0.53.x (IBC v10, CometBFT v0.38) | v29.0.0-rc.1 #4657 "Upgrade to Cosmos SDK v0.53.0", "Bump minimum compatible Cosmos SDK version to v0.50.0"; v29.8.0 #4874 bumps to v0.53.6; `ignite version` on v29.10.1 prints v0.53.6 |
| v30.0.0-rc.2 (pre-release) | v0.55.0, IBC-Go v11.2.0, CometBFT v0.40.0 | rc.2 release notes / #5001; "Ignite CLI v30 works with both v0.55.x and v0.53.x chains" |

Rules of thumb:

- Use the Ignite major that matches the SDK in your chain's `go.mod`. A v29 Ignite on an SDK v0.50 chain is supported (minimum compatible v0.50.0); older chains need the older Ignite.
- Ignite ≤ v28 cannot parse a `go.mod` that uses the Go 1.24 `tool` directive (`unknown block type: tool`). Upgrade Ignite, or build with plain `go build`.
- v30 removes `x/params`, `x/group`, `x/circuit`, and `x/nft` from the template. Upgrading a v29-scaffolded chain to SDK v0.55 is manual: follow https://docs.ignite.com/migration/v30.0.0 (dependency bumps, import paths, app wiring, IBC v11). To keep a v29 chain as is while using the v30 binary, the migration guide says to run `ignite cosmos doctor`.

## v30 command layout (verified from `v30.0.0-rc.2 --help`)

```
ignite scaffold realm|package      # gno.land
ignite chain serve|deploy|call|query|send|test   # gno.land dev chain (serve: --chain-id dev, --remote tcp://127.0.0.1:26657)
ignite account …                   # gno keybase
ignite generate ts-client          # gno client
ignite cosmos scaffold …           # Cosmos SDK: chain, module, message, query, list, map, single, type, params, configs, packet, migration, vue, react, chain-registry
ignite cosmos chain serve|build|init|faucet|simulate|debug|lint|modules
ignite cosmos generate proto-go|ts-client|composables|openapi
ignite cosmos account|testnet
ignite cosmos doctor               # hidden from `ignite cosmos --help` but present
```

Not matching the docs: the migration guide says top-level `chain`/`generate`/`testnet` "print a deprecation error"; on rc.2 `ignite chain build` instead prints the gno `chain` help, and `ignite doctor` prints root help. Do not rely on a helpful error; check `ignite version` first.
