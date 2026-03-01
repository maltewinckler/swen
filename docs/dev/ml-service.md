# ML Service

The ML service is a separate **FastAPI** microservice (`swen-ml`), communicating with the backend over HTTP.

## Package Layout

```
services/ml/swen_ml/
├── api/            ← FastAPI app, routers (/classify, /examples, /health)
├── config/         ← pydantic-settings for ML-specific config
├── data_models/    ← domain models (Anchor, Example, Noise, Enrichment)
├── inference/
│   ├── shared.py               ← SharedInfrastructure dataclass
│   ├── _models/                ← Encoder protocol + backends (sentence-transformers, HuggingFace)
│   └── classification/
│       ├── orchestrator.py     ← ClassificationOrchestrator
│       ├── tiers.py            ← PreprocessingTier, ExampleTier, EnrichmentTier, AnchorTier
│       ├── context.py          ← PipelineContext, TransactionContext
│       ├── result.py           ← ClassificationResult
│       ├── classifiers/
│       │   ├── anchor.py       ← AnchorClassifier (account embedding similarity)
│       │   └── example.py      ← ExampleClassifier (user history k-NN)
│       ├── enrichment/
│       │   ├── service.py      ← EnrichmentService (keyword + SearXNG)
│       │   ├── keywords/       ← FileKeywordAdapter + keywords_de.txt
│       │   └── search/         ← SearXNGAdapter
│       └── preprocessing/
│           └── text_cleaner.py ← TextCleaner + NoiseModel
├── storage/        ← SQLAlchemy models + async repos (swen_ml DB)
├── training/       ← Example ingestion, embedding computation, storage
└── evaluation/     ← Offline evaluation tooling (__main__.py)
```

## Lifespan

On startup, the ML service performs the following steps in order (FastAPI `lifespan`):

1. **DB init** — Create `swen_ml` schema if it doesn't exist
2. **Encoder load** — Load the configured sentence encoder from HuggingFace (or local cache); default: `paraphrase-multilingual-MiniLM-L12-v2`
3. **Warm-up** — Run one dummy inference to compile CUDA/CPU kernels
4. **Enrichment init** — Verify SearXNG connectivity (non-fatal if unreachable)
5. **SharedInfrastructure** — Assemble the shared object and attach to `app.state`

Until step 3 completes, the `/health` endpoint returns `{"status": "loading"}`. The backend waits for a healthy ML service before sending classification requests.

## SharedInfrastructure

All request handlers receive a `SharedInfrastructure` object via FastAPI `Depends`:

```python
@dataclass
class SharedInfrastructure:
    encoder: Encoder          # protocol — sentence-transformers or HuggingFace backend
    settings: Settings        # ML service config
    keyword_adapter: KeywordPort | None = None    # keyword enrichment (always loaded)
    searxng_adapter: SearXNGAdapter | None = None # web search enrichment (optional)
```

This avoids re-loading the model on every request and centralises resource management.

## Storage

The ML service uses its own **SQLite / PostgreSQL** database (`swen_ml`), separate from the main `swen` database. This separation means:

- The ML service can be scaled or replaced independently
- ML training data (examples, embeddings) does not pollute the main DB
- The main backend never reads ML storage directly

Tables:
- `user_examples` — stored transaction texts + their known counter-account + embedding vector
- `anchor_embeddings` — per-account anchor embeddings (account name/description encoded as vectors)
- `user_noise_models` — per-user IDF noise model (boilerplate token frequencies)
- `enrichment_cache` — SearXNG lookup results (keyed by query hash, with TTL)

## Training Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Backend
    participant MLService

    User->>Backend: POST /transactions/{id}/post
(with corrected account)
    Backend->>MLService: POST /examples
{text, account_id, account_number}
    MLService->>MLService: Encode text → embedding vector
    MLService->>MLService: Store in user_examples table
    Note over MLService: Available for ExampleClassifier on next classify request
```

The backend sends a training example whenever a transaction is posted **with a correction** (or on first post if no suggestion was made). No retraining loop — the example is immediately available for k-NN retrieval.

## Evaluation Tooling

`swen_ml/evaluation/__main__.py` provides an offline evaluation script:

```bash
uv run --package swen-ml python -m swen_ml.evaluation \
    --test-set data/eval.jsonl \
    --output eval_results.json
```

This runs the full classification pipeline against a labelled test set and reports accuracy per tier, per account, and an overall precision/recall breakdown.
