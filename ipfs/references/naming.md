# Naming, gateways, and shipping sites

Content is immutable; names are the mutable layer. Two mechanisms: IPNS (cryptographic) and DNSLink (DNS-based, pragmatic).

## IPNS

A name = hash of a public key; the key holder signs records pointing at the current CID.

```bash
ipfs key gen mysite                          # or use 'self'
ipfs name publish --key=mysite /ipfs/<CID>   # -> /ipns/k51q…
ipfs name resolve /ipns/k51q…
```

Honest properties (July 2026):
- Default record **TTL is 5 min** (was 1 h; changed in Kubo v0.34) — updates propagate reasonably now, but resolution is still slower than a straight CID fetch.
- **Records expire** (~48 h lifetime; Kubo republishes every 4 h) — the key-holding node must stay online, or configure `Ipns.DelegatedPublishers` / export records with `ipfs name get|put` (v0.40+).
- IPNS-over-PubSub exists as experimental opt-in (`Ipns.UsePubsub`) — the 2023 deprecation was reversed.
- Losing the key = losing the name. Back up `~/.ipfs/keystore`.

Good for: app-updatable pointers without DNS. Wrong for: high-frequency mutable state (use a database or OrbitDB).

## DNSLink (the pragmatic choice for websites)

```
_dnslink.docs.example.com   TXT   "dnslink=/ipfs/bafybei…"
```

- Resolves on any gateway (`https://<gateway>/ipns/docs.example.com`) and in IPFS-aware clients (`ipfs://docs.example.com`).
- Faster than IPNS (docs recommend it for sites); updates = change the TXT record.
- Trade-off: reintroduces DNS/registrar trust. Pair with ENS or IPNS when that matters.

## Ship a site

1. Build any static site — **use relative asset paths** (you may be served under `/ipfs/<CID>/`).
2. `ipfs add --cid-version 1 -r dist/` → root CID.
3. Remote-pin the root CID (see pinning.md).
4. Point `_dnslink` TXT (or IPNS/ENS) at the new CID. Old CIDs remain fetchable — rollback is a pointer change.

SPA note: client-side routers need `index.html` fallback handling — gateways serve `/ipfs/<CID>/missing-path` as 404 unless you use `_redirects` (supported by the gateway spec for web hosting) or hash routing.

## Gateways (state as of July 2026 — the big recent shift)

- **Local**: `http://127.0.0.1:8080/ipfs/<CID>` — always preferred in dev.
- **Public ipfs.io / dweb.link are winding down**: rate-limited, best-effort, top-level browser navigations redirect to **inbrowser.link** (Service Worker Gateway). Never build production apps on them.
- **Path vs subdomain**: `gw.tld/ipfs/<cid>` (path) breaks origin isolation — every site shares one origin. `<cid>.ipfs.gw.tld` (subdomain) gives per-site origins; requires CIDv1 base32. Prefer subdomain.
- **Trustless gateways** (spec: reliable, 2026) serve raw blocks / CAR files so the *client* verifies hashes — `trustless-gateway.link` is a public endpoint; pair with `@helia/verified-fetch` (see apps.md).
- **Self-host** for production: Rainbow (gateway daemon) + someguy (delegated routing), or full Kubo behind a reverse proxy on 8080.
- Browser support: Brave removed native ipfs:// in Aug 2024; use IPFS Companion (extension) or the Service Worker Gateway.

## Debugging resolution

```bash
ipfs resolve -r /ipns/docs.example.com     # DNSLink -> CID
dig +short TXT _dnslink.docs.example.com
ipfs routing findprovs <CID>               # any providers?
```

https://check.ipfs.network tests retrievability from the outside.
