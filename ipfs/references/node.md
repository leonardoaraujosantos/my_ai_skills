# Running and driving a Kubo node

Kubo (Go) is the reference implementation — v0.42.x as of July 2026. Node 20-era tutorials referencing go-ipfs are the same lineage, renamed.

## Install & run

```bash
brew install ipfs          # macOS; other OS: https://dist.ipfs.tech + install.sh
ipfs init                  # creates ~/.ipfs + peer identity
ipfs daemon                # joins the network (leave running)
ipfs id                    # your PeerID + listen addrs
open http://127.0.0.1:5001/webui
```

- Ports: **4001** p2p (open/forward this), **5001** API (localhost only — full control, no auth, never expose), **8080** local gateway (safe to proxy).
- Kubo v0.41+ has built-in `ipfs update`.
- Since v0.34, **AutoTLS** auto-provisions a Let's Encrypt cert at `*.<PeerID>.libp2p.direct` so browsers can dial your node over WSS.
- Config is `~/.ipfs/config`; since v0.37 bootstrap/routing default to `"auto"` (AutoConf) — inspect the resolved values with `ipfs config show --expand-auto`.

## Everyday CLI

```bash
ipfs add --cid-version 1 file.bin      # add + pin locally -> CID
ipfs add --cid-version 1 -r ./site     # directory; names preserved (UnixFS)
ipfs cat <CID>                         # stream
ipfs get <CID> -o out/                 # to disk
ipfs ls <dirCID>                       # list a directory CID
ipfs dag get <CID>                     # inspect the DAG node (json)

ipfs pin add <CID>                     # protect from GC
ipfs pin ls --type=recursive
ipfs pin rm <CID> && ipfs repo gc      # release + reclaim space
```

**CIDv1 gotcha (teach this):** CIDv1 base32 is the official recommendation (subdomain-gateway safe), but plain `ipfs add` still defaults to CIDv0 (`Qm…`). Always pass `--cid-version 1` or set `Import.CidVersion=1`. Convert existing: `ipfs cid format -v 1 -b base32 <Qm…>`. Same bytes, same content, different text form.

## Cache vs pin vs provide — the model that prevents 90% of confusion

- `ipfs add` stores blocks **on your node only**; nothing is uploaded anywhere.
- Fetched content sits in **cache** and is evictable by `ipfs repo gc`; **pins** are exempt.
- **Provider records** in the DHT announce what you have. Others can fetch only while your daemon is online and records are fresh.

```bash
ipfs routing findprovs <CID>    # who claims to have it
ipfs routing provide <CID>      # re-announce now (v0.42+: ipfs provide once)
ipfs id <PeerID>                # inspect a provider
```

Providing at scale: Provide Sweep (default since v0.39) makes announcing many CIDs cheap; `ipfs stats provide` shows progress.

## Retrieval path (what to say when asked "how does a fetch work?")

1. Local cache? done. 2. Find providers: **Amino DHT** + delegated HTTP routing (`/routing/v1`, IPNI/cid.contact — Kubo `Routing.Type=auto` uses both). 3. libp2p dials (TCP/QUIC/WebTransport/WebRTC, NAT traversal). 4. **Bitswap** pulls blocks from several peers in parallel, hash-verifying each. Downloaders re-serve from cache — popular content gets faster.

## Ops notes

- Storage: `ipfs repo stat`; default `StorageMax` 10GB — raise for real use.
- A laptop is not persistence: for anything that must stay up, run a small always-on node (VPS) or use a pinning service (see pinning.md).
- Multiple nodes replicating a pinset → **IPFS Cluster** (ipfscluster.io).
- Docker: `ipfs/kubo` image. Headless server gateway only: **Rainbow**; delegated-routing server: **someguy**.
