# Deploying sites to the permaweb

Static frontends only (Svelte/React/Vue/plain HTML). Build → upload assets as an ANS-104 bundle → path manifest maps routes → (optionally) point an ArNS name at the new manifest.

> Safety: deploys upload permanently (permanence gate) and ArNS purchases cost ARIO (spending gate). Use hash-router or proper fallbacks for SPAs.

## How updates work on an immutable web

- Every asset and every manifest is a permanent transaction.
- A **manifest** maps paths (`index.html`, `assets/app.js`, 404 fallback) to data-item ids.
- A new release = new manifest. The **ArNS name is the only mutable pointer** — repoint it to the new manifest. Old versions stay resolvable forever; rollback is a pointer change.

## Option A (ar.io official): `@ar.io/deploy`

```bash
npm i -D @ar.io/deploy
export DEPLOY_KEY=$(base64 -i wallet.json)     # wallet must own/control the ArNS name
ario-deploy deploy --deploy-folder ./dist --arns-name myapp --use-arns
```

- On-demand payment without pre-funded credits: `--on-demand ario --max-token-amount 2.0`
- GitHub Action: `ar-io-deploy@v1` — supports PR-preview deployments (deploys each PR to an undername).

## Option B: `@permaweb/deploy` (v5+, successor of permaweb-deploy)

```bash
pnpm add -D @permaweb/deploy
export DEPLOY_KEY=$(base64 -i wallet.json)
permaweb-deploy deploy --use-names --name my-app --deploy-folder ./dist --sig-type arweave
```

## Manifest without a deploy tool

`turbo upload-folder` / `turbo.uploadFolder()` auto-generates the manifest and returns its txid — the site is live at `https://arweave.net/<manifest-txid>` immediately. Deploy tools only add the ArNS repointing step.

Manifest format (`application/x.arweave-manifest+json`):

```json
{
  "manifest": "arweave/paths",
  "version": "0.2.0",
  "index": { "path": "index.html" },
  "fallback": { "id": "<txid-of-404-or-index>" },
  "paths": {
    "index.html": { "id": "<txid>" },
    "assets/app.js": { "id": "<txid>" }
  }
}
```

## ArNS (Arweave Name System)

- Human-readable names on the ar.io network, bought/leased with **ARIO** at https://arns.arweave.net (spending gate).
- Resolve on any gateway: `https://myapp.ar.io`, `https://myapp.<other-gateway>`.
- **Undernames** for environments/versions: `staging_myapp.ar.io` — cheap way to do previews and staged rollouts.
- Name records have a TTL; propagation of a repoint is minutes, not instant.

## SPA gotchas

- Client-side routing needs the manifest `fallback` to point at `index.html` (or use hash routing) — otherwise deep links 404.
- Use **relative asset paths** (`./assets/...`, or Vite `base: './'`); absolute `/assets/...` breaks when served under `/<txid>/`.
- Never hard-code one gateway in the app; derive from `window.location` when possible.

## CI checklist

1. Store the wallet as a base64 secret (`DEPLOY_KEY`), never in the repo.
2. Build → deploy tool of choice → repoint ArNS.
3. Log the manifest txid in the job output — that id is the permanent, auditable release artifact.
