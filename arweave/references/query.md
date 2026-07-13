# Querying Arweave (GraphQL + gateways)

Tags are the schema; GraphQL is the index. ArQL is historical — do not use.

## Endpoints (July 2026)

| Endpoint | Notes |
|---|---|
| `https://arweave.net/graphql` | Classic, widely mirrored in docs |
| `https://arweave-search.goldsky.com/graphql` | High-performance, full coverage |
| `https://turbo-gateway.com/graphql` | Full indexing incl. recent bundles, has playground |
| `https://<any ar.io gateway>/graphql` | Serves only what that gateway indexed |

If recent bundled items are missing from one endpoint, try goldsky/turbo-gateway — indexing lag differs per gateway.

## Query patterns

Find by tags (the workhorse):

```graphql
query {
  transactions(
    tags: [
      { name: "App-Name", values: ["MyApp"] }
      { name: "Type", values: ["certificate", "receipt"] }   # OR within values
    ]
    owners: ["<wallet-address>"]      # optional
    first: 25
    sort: HEIGHT_DESC
  ) {
    pageInfo { hasNextPage }
    edges {
      cursor
      node {
        id
        owner { address }
        tags { name value }
        data { size type }
        block { height timestamp }
        bundledIn { id }              # parent bundle if ANS-104
      }
    }
  }
}
```

Pagination: pass `after: "<cursor>"` with the last edge's cursor; loop while `hasNextPage`.

By transaction id(s): `transactions(ids: ["<txid>"]) { ... }` or single `transaction(id: "<txid>")`.

curl example:

```bash
curl -s -X POST https://arweave.net/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ transactions(tags:[{name:\"App-Name\",values:[\"MyApp\"]}] first:10){ edges { node { id tags { name value } } } } }"}' | jq .
```

## Fetching the data itself

GraphQL returns metadata only. Get content from any gateway:

```bash
curl https://arweave.net/<txid>            # raw data, served with its Content-Type
curl https://ar-io.net/<txid>              # same data, different gateway
curl https://arweave.net/raw/<txid>        # bypass manifest resolution
```

Notes:
- Multiple gateways serve the same dataset — never hard-code a single gateway in app code; make it configurable.
- Block-level info: `https://arweave.net/tx/<txid>`, `/tx/<txid>/status`, `/block/height/<n>`.
- AO messages are also Arweave data items and are queryable the same way (tags like `Data-Protocol: ao`, `Type: Message`, `From-Process`), or browse them on https://ao.link.
