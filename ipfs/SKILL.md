---
name: ipfs
description: Operate IPFS as a developer — run and drive a Kubo node (add/cat/pin/gc, CIDv1 gotchas, provider records), keep data alive (remote pinning services, Pinning Service API, Filecoin), name and ship sites (IPNS, DNSLink, gateways incl. trustless/verified retrieval), and build apps (Helia, @helia/verified-fetch, Pinata SDK, CID-on-chain patterns). Includes privacy rules for public content-addressed data and the 2025-26 public-gateway wind-down. Use when the user says "IPFS", "CID", "Kubo", "Helia", "pin/pinning", "IPNS", "DNSLink", "ipfs gateway", "content addressing", "Pinata", "Storacha", or "Filecoin storage".
argument-hint: [node|pin|name|app] [topic]
---

# IPFS — Developer Operations

Playbooks for the 2026 IPFS toolchain. Facts and commands verified against official docs (docs.ipfs.tech, specs.ipfs.tech, probelab.io, ipshipyard.com) on **2026-07-13** — this ecosystem churns; re-check the docs at the bottom when in doubt.

| Task | Reference file |
|------|----------------|
| Run/drive a node: Kubo CLI, CIDs, pin/gc, providing | `references/node.md` |
| Keep data alive: remote pinning, services, Filecoin | `references/pinning.md` |
| Naming & sites: IPNS, DNSLink, gateways, deploys | `references/naming.md` |
| Build apps: Helia, verified fetch, SDKs, patterns | `references/apps.md` |

**How to use this skill:** identify the task, read the matching reference file before answering, then run/write code against the user's project. Prefer the modern stack — Helia, CIDv1, verified retrieval, Pinning Service API. js-ipfs, ipfs-http-client, and building on public gateways are legacy patterns.

## ⚠️ Safety gates

**Publicity gate — added data is public and effectively unrecallable.**
- Everything on the public IPFS network is fetchable by anyone with the CID, and once other nodes pin it you cannot delete it. Before adding real data: show the user what will be added and check it for PII/secrets. Encryption limits access, **not existence** — encrypt sensitive payloads client-side before `ipfs add`, keys stay with the user.
- `ipfs add` alone is local, but the daemon announces provider records — treat "added while daemon runs" as published.

**Spending gate — require explicit approval in the conversation for:**
- Paid pinning plans / paid tiers (Pinata, Storacha, Filebase, 4EVERLAND)
- Filecoin deals or any FIL/token transaction
- Infra spend (VPS for an always-on node, dedicated gateways)

**Keys & tokens:**
- Pinning-service tokens (e.g. `PINATA_JWT`) live in env vars, never in code or logs.
- Never expose the Kubo API port **5001** beyond localhost — it has no auth and full node control. The gateway port 8080 is the safe one to reverse-proxy.
- The node identity key lives in `~/.ipfs`; treat it like any private key. IPNS names die with lost keys — back them up deliberately.

## Core mental model (30 seconds)

- **Content addressing**: a CID identifies bytes by hash, not location. Same bytes ⇒ same CID, any provider can serve it, every block is verifiable.
- **CID = multibase + multicodec + multihash** (default base32 / dag-pb or raw / sha2-256). CIDv1 (`bafy…`) is the recommendation; legacy CIDv0 (`Qm…`) still exists — and **plain `ipfs add` still emits CIDv0**: pass `--cid-version 1`.
- **Files → chunks (256 KiB default) → Merkle DAG**; the root hash is the CID. Identical blocks dedupe; UnixFS preserves names/dirs.
- **Retrieval** = find providers (Amino DHT + delegated HTTP routing / IPNI) → dial with libp2p → Bitswap blocks from many peers, hash-checking each.
- **Adding is local; serving is voluntary.** Cache ≠ pin ≠ provided. Persistence is a service you arrange (your nodes, a pinning service, Filecoin) — nobody is paid by the protocol to keep your data. That's the core difference vs Arweave's endowment.
- **Mutability** is a pointer layer: IPNS (key-signed records, 5-min TTL default) or DNSLink (`_dnslink` TXT record — faster, DNS-trusted).

## Known-stale traps (do not recommend)

| Stale (pre-2025 tutorials) | Current (July 2026) |
|---|---|
| js-ipfs / ipfs-http-client | **Helia** (+ @helia/unixfs, @helia/verified-fetch) |
| Build apps on ipfs.io / dweb.link | Rate-limited, winding down → verified fetch, inbrowser.link, self-hosted Rainbow |
| web3.storage / free NFT.Storage / Infura IPFS / Estuary | **Storacha** / paid NFT.Storage (Lighthouse) / gone / gone |
| `Qm…` CIDs as the norm | CIDv1 base32 (`ipfs add --cid-version 1`) |
| Brave's native ipfs:// support | Removed Aug 2024; use IPFS Companion or Service Worker Gateway |
| "IPFS stores your file on the network" | Adding is local; arrange pinning for persistence |

## Official docs (current)

- Docs — https://docs.ipfs.tech · Specs — https://specs.ipfs.tech
- Kubo — https://github.com/ipfs/kubo · Helia — https://github.com/ipfs/helia (+ ipfs-examples/helia-examples)
- Network measurements — https://probelab.io · Maintainers' blog — https://ipshipyard.com/blog + https://blog.ipfs.tech
- CID inspector — https://cid.ipfs.tech · Papers: Benet 2014 (arXiv 1407.3561), Trautwein et al. SIGCOMM 2022
