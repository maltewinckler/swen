# Web Enrichment

Many bank transaction purposes are cryptic abbreviations like `KARTE 09.05 UM 14:35 UHR` — not enough text for the embedding model to find a good match. **Web enrichment** solves this by looking up the counterparty name online before classification.

## What Enrichment Does

When a transaction arrives for classification, the enrichment step:

1. Extracts the **counterparty name** (and optionally the purpose text)
2. Searches a self-hosted **SearXNG** instance for information about that merchant
3. Appends the top search result snippet to the transaction text
4. Passes the enriched text to the embedding encoder

**Example:**

| Without enrichment | With enrichment |
|---|---|
| `KARTE 09.05 EDEKA` | `KARTE 09.05 EDEKA — EDEKA ist ein deutsches Lebensmittelnetz...` |

The embedding for the enriched version clusters much closer to other "Groceries" examples.

## SearXNG — Why Self-Hosted

SWEN uses [SearXNG](https://docs.searxng.org/) — a self-hosted, privacy-respecting meta-search engine. Reasons:

- **No API key needed** — SearXNG aggregates public search engines, no paid subscription
- **No data leakage** — your transaction counterparty names never reach Google or Bing directly
- **Configurable** — you can point SearXNG at specific search engines or disable it entirely
- **Runs alongside SWEN** — included in `docker-compose.yml`, no extra setup

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `SWEN_ML_ENRICHMENT_SEARXNG_URL` | *(none)* | URL of your SearXNG instance. Set to `http://searxng:8080` in Docker |
| `SWEN_ML_ENRICHMENT_ENABLED` | `true` | Set to `false` to disable enrichment entirely |
| `SWEN_ML_ENRICHMENT_TIMEOUT_SECONDS` | `3` | Max wait time per lookup |
| `SWEN_ML_ENRICHMENT_CACHE_TTL_HOURS` | `168` | How long lookup results are cached (default: 7 days) |

Set these in `config/.env`:

```bash
SWEN_ML_ENRICHMENT_SEARXNG_URL=http://searxng:8080
SWEN_ML_ENRICHMENT_ENABLED=true
```

## When Enrichment Is Skipped

Enrichment is skipped (gracefully) when:

- `SWEN_ML_ENRICHMENT_ENABLED=false`
- The SearXNG service is unreachable (connection refused, DNS failure)
- The lookup takes longer than `SWEN_ML_ENRICHMENT_TIMEOUT_SECONDS`
- No meaningful counterparty name could be extracted
- The result is already cached from a previous lookup

In all these cases, classification falls through to Tier 1 with the un-enriched text. Enrichment failure never prevents classification.

## Caching

Enrichment results are cached in the ML service's SQLite database keyed by the (normalised) counterparty name. The default TTL is 7 days. This means:

- `REWE MARKT HAMBURG` only triggers one SearXNG lookup, then uses the cached description for all future REWE transactions
- The cache warms up quickly after the first few hundred transactions

## Rate Limiting

SearXNG itself applies rate limiting to the upstream search engines it queries. SWEN's enrichment client does not add additional rate limiting beyond the timeout. If you are running a high-volume import (thousands of transactions), enrichment may be throttled by SearXNG's upstream limits. In that case, set `SWEN_ML_ENRICHMENT_ENABLED=false` for the initial bulk import, then re-enable it for ongoing use.

## Disabling SearXNG Entirely

If you prefer not to run SearXNG at all:

1. Set `SWEN_ML_ENRICHMENT_ENABLED=false` in `config/.env`
2. Comment out the `searxng` service in `docker-compose.yml`

Classification still works via Tier 0 (IBAN anchor), Tier 1 (embeddings, slightly less effective), and Tier 2 (keyword patterns).
