# Sentence Embeddings

SWEN's Tier 1 classification uses **sentence embeddings** to find transactions that are semantically similar to past examples, even when the exact wording differs.

## The Model

SWEN uses [`deutsche-telekom/gbert-large-paraphrase-cosine`](https://huggingface.co/deutsche-telekom/gbert-large-paraphrase-cosine) from HuggingFace.

| Property | Value |
|---|---|
| Architecture | BERT-large |
| Language | German |
| Training objective | Paraphrase similarity (cosine) |
| Embedding dimension | 1024 |
| Model size | ~1.5 GB |
| Licence | MIT |

### Why German?

FinTS transaction purposes (`Verwendungszweck`) are almost always in German. Using a German-language BERT model gives significantly better semantic clustering than a multilingual model — German merchant names, abbreviations, and purpose text patterns are well-represented in the training data.

### Why `gbert-large-paraphrase-cosine`?

- **Paraphrase-optimised**: explicitly trained to produce similar embeddings for sentences that mean the same thing. "REWE MARKT 123 HAMBURG" and "REWE SAGT DANKE 456" both embed close to each other.
- **Cosine distance**: embeddings are already normalised, so cosine similarity is the natural distance metric.
- **Deutsche Telekom model**: tested extensively on German NLP benchmarks.

## HuggingFace Cache

The model is downloaded once on first startup and cached. In Docker:

```yaml
volumes:
  ml-model-cache:

services:
  ml:
    volumes:
      - ml-model-cache:/root/.cache/huggingface
```

The environment variable `HF_HOME` can override the cache directory.

!!! info "First-run download"
    The first time the ML service starts, it downloads ~1.5 GB from HuggingFace. Classification requests will return 503 until the download completes. Monitor with:
    ```bash
    docker compose logs -f ml
    ```
    Subsequent restarts load the model from the local cache (a few seconds).

## Encoder Backend

SWEN uses `sentence-transformers` as the encoder backend. The `SentenceTransformer` class handles tokenisation, batching, and embedding extraction.

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "deutsche-telekom/gbert-large-paraphrase-cosine",
    cache_folder="/root/.cache/huggingface",
)
embedding = model.encode("REWE MARKT 123 HAMBURG", normalize_embeddings=True)
```

## Pooling Strategy

`gbert-large-paraphrase-cosine` uses **mean pooling** over the last hidden states of all non-padding tokens. This is configured in the model's `1_Pooling/config.json` on HuggingFace and applied automatically by `sentence-transformers`.

## Similarity Search

Stored example embeddings are retrieved from the ML service's database and compared using **cosine similarity**:

$$
\text{similarity}(A, B) = \frac{A \cdot B}{\|A\| \|B\|}
$$

Since embeddings are already L2-normalised (`normalize_embeddings=True`), this reduces to a simple dot product — fast and numerically stable.

The top-k nearest neighbours (k=5 by default) vote on the counter-account. If the top neighbour exceeds the confidence threshold, its account is returned.

## Warm-up

On service startup, SWEN loads the model and runs a single dummy inference to ensure the CUDA/CPU kernels are compiled before the first real request:

```python
# Warm-up call in lifespan
model.encode("warm-up", normalize_embeddings=True)
```

This prevents a slow first-request penalty.
