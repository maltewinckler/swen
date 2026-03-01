# Sentence Embeddings

SWEN's Tier 1 classification uses **sentence embeddings** to find transactions that are semantically similar to past examples, even when the exact wording differs.

## The Model

The encoder model is **configurable** via the `SWEN_ML_ENCODER_MODEL` environment variable. The default is:
[`paraphrase-multilingual-MiniLM-L12-v2`](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)

| Property | Value (default model) |
|---|---|
| Architecture | MiniLM-L12 |
| Language | Multilingual (50+ languages, including German) |
| Training objective | Paraphrase similarity (cosine) |
| Embedding dimension | 384 |
| Model size | ~120 MB |
| Licence | Apache 2.0 |

### Why a paraphrase model?

FinTS transaction purposes (`Verwendungszweck`) contain many variations of the same merchant — `REWE MARKT 123 HAMBURG`, `REWE SAGT DANKE 456`. A paraphrase-optimised model is explicitly trained to embed such variations close to each other, making cosine similarity a reliable clustering signal.

### Custom models

Any model supported by the configured encoder backend can be substituted. For higher accuracy (at the cost of a larger download and slower inference), replace the default with a larger German-specific model such as [`deutsche-telekom/gbert-large-paraphrase-cosine`](https://huggingface.co/deutsche-telekom/gbert-large-paraphrase-cosine).

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

SWEN supports two encoder backends, selected via `SWEN_ML_ENCODER_BACKEND`:

| Backend | `SWEN_ML_ENCODER_BACKEND` value | Notes |
|---|---|---|
| `sentence-transformers` | `sentence-transformers` | Recommended — automatic pooling and normalisation |
| HuggingFace `transformers` | `huggingface` | Manual pooling via `SWEN_ML_ENCODER_POOLING` (`mean` / `cls` / `max`) |

**`sentence-transformers` example:**

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
embedding = model.encode("REWE MARKT 123 HAMBURG", normalize_embeddings=True)
```

**HuggingFace backend** additionally respects `SWEN_ML_ENCODER_NORMALIZE`, `SWEN_ML_ENCODER_MAX_LENGTH`, and `SWEN_ML_ENCODER_POOLING`.

## Pooling Strategy

`gbert-large-paraphrase-cosine` uses **mean pooling** over the last hidden states of all non-padding tokens. This is configured in the model's `1_Pooling/config.json` on HuggingFace and applied automatically by `sentence-transformers`.

## Similarity Search

Stored example embeddings are retrieved from the ML service's database and compared using **cosine similarity**:

$$
\text{similarity}(A, B) = \frac{A \cdot B}{\|A\| \|B\|}
$$

Since embeddings are already L2-normalised (`normalize_embeddings=True`), this reduces to a simple dot product — fast and numerically stable.

The **top-2** nearest neighbours are compared. A match is accepted when:

- the best similarity ≥ **0.85** (high confidence), or
- the best similarity ≥ **0.70** *and* the margin over the 2nd-best ≥ **0.10**

The margin check prevents accepting an ambiguous result when two accounts score similarly close.

## Warm-up

On service startup, SWEN loads the model and runs a single dummy inference to ensure the CUDA/CPU kernels are compiled before the first real request:

```python
# Warm-up call in lifespan
model.encode("warm-up", normalize_embeddings=True)
```

This prevents a slow first-request penalty.
