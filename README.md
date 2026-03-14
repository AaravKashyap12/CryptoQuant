<div align="center">
  <img src="frontend/public/vite.svg" alt="logo" width="80" height="auto" />
  <h1>CryptoQuant Analytics</h1>
  <p>
    A full-stack cryptocurrency price forecasting platform powered by a Hybrid
    LSTM–CNN ensemble, Monte Carlo Dropout uncertainty estimation, and a
    Redis-backed 3-tier prediction cache.
  </p>

<p>
  <a href="https://github.com/AaravKashyap12/CryptoQuant/graphs/contributors">
    <img src="https://img.shields.io/github/contributors/AaravKashyap12/CryptoQuant" alt="contributors" />
  </a>
  <a href="https://github.com/AaravKashyap12/CryptoQuant/stargazers">
    <img src="https://img.shields.io/github/stars/AaravKashyap12/CryptoQuant" alt="stars" />
  </a>
  <a href="https://github.com/AaravKashyap12/CryptoQuant/actions/workflows/test.yml">
    <img src="https://github.com/AaravKashyap12/CryptoQuant/actions/workflows/test.yml/badge.svg" alt="tests" />
  </a>
</p>

<h4>
  <a href="https://cryptoquant.vercel.app">Live Demo</a> ·
  <a href="https://github.com/AaravKashyap12/CryptoQuant/issues">Report Bug</a>
</h4>
</div>

---

## What's New in v2.0.0

This release is a significant overhaul focused on prediction accuracy, inference reliability, and production robustness. Every layer of the stack was touched.

### Model Architecture
- **`build_model` parallelised** — LSTM and CNN now run in parallel (both see the raw sequence), replacing the old sequential pipeline where CNN compressed features *before* LSTM saw them. This was a fundamental architecture flaw.
- **LSTM capacity doubled** — 128 units (up from 64), giving the model richer temporal representations.
- **CNN depth increased** — two Conv1D layers (64 + 32 filters) replace the single-layer design, with LeakyReLU activations throughout.
- **CNN branch now stochastic** — Dropout was missing on the CNN branch in `build_hybrid_model`, making half the model deterministic during MC Dropout inference. Confidence bands were systematically too narrow. Fixed.
- **No normalisation layers** — BatchNorm/LayerNorm removed; they interact incorrectly with `training=True` Dropout inference.
- **Deeper forecast head** — Dense(64) → Dense(32) → output, replacing the single Dense(32).

### Training Pipeline
- **Per-coin configuration (`COIN_CONFIG`)** — BTC/ETH now train on 1500 rows with lookback=60; BNB trains on 2000 rows with lookback=20. Previously all coins used the same limit and lookback regardless of data availability.
- **Mock data guard** — training is refused if the data source is Mock, preventing garbage models from being registered.
- **`ReduceLROnPlateau` added** — LR halves on val_loss plateau (patience=5, min=1e-6); EarlyStopping patience raised to 15.
- **Training metadata enriched** — `trained_at`, `train_samples`, `test_samples` now saved alongside MAE/RMSE.

### Prediction & Inference
- **3-tier prediction cache** — Redis → DB (`cached_predictions` table) → live inference. Typical response: < 100ms.
- **`run_prediction_batch` introduced** — pre-computes all 5 coin forecasts at n_iter=20 after training, so the API never cold-computes on user requests.
- **`tf.function` compiled inference** — a `_compiled_fns` cache wraps each model in a compiled TF graph, reducing per-call CPU overhead by ~15–30%.
- **Explicit shape guard** — input shape is validated before every inference call; mismatches now raise loudly instead of silently producing wrong predictions.
- **Sentiment coverage matched** — inference now fetches 500 rows of Fear & Greed data (was 100), matching training coverage more closely.

### Evaluation & Backtest
- **Backtest actual price fixed** — the old backtest compared predictions against `close[i]` (last candle of the *input* window). Fixed to compare against `close[i+1]` (the actual next-day close). Backtest accuracy metrics were inflated.
- **Backtest uses MC Dropout** — replaced `model.predict()` (deterministic) with 5-pass MC Dropout averaging to match production behaviour.
- **`evaluate_model` uses MC Dropout** — same fix; training-time evaluation now reflects actual inference quality.
- **Scaler leakage fixed** — backtest no longer transforms the entire DataFrame upfront. Each prediction window is scaled independently, matching real inference and eliminating distribution leakage.

### Data Fetching
- **Per-symbol exchange priority** — BNB and ADA now prefer KuCoin (1500+ rows) over Coinbase (143 rows). Old code starved these coins of training data.
- **Redis-aware 2-tier OHLCV cache** — Redis (shared across workers, survives restarts) + in-process dict (dev/fallback).
- **`source` column survives Redis round-trip** — was silently dropped during serialisation; all callers that guard on `df["source"] == "Mock"` now work correctly.
- **Neutral sentiment fallback** — on API failure, returns a DataFrame of 50s instead of `None`, preventing NaN propagation through the feature set.
- **Interval normalisation** — `fetch_klines(interval=None)` now canonicalises to `"1d"` before building the cache key, eliminating duplicate cache entries.

### Feature Engineering
- **RSI uses Wilder's smoothing** — replaced `rolling(14).mean()` with `ewm(alpha=1/14, adjust=False)`. The old formula produced incorrect RSI values not matching any trading platform.
- **`ema_99` replaced by `ema_50`** — ema_99 forced ~99 NaN warmup rows to be dropped, wasting ~20% of a 500-row dataset with minimal predictive benefit. ema_50 retains the long-term trend signal with far smaller warmup cost.
- **`dropna` moved to preprocessor** — `add_technical_indicators` no longer calls `dropna()`. The call is now centralised in `preprocess.py` *after* the sentiment merge, so row counts stay aligned across all features.
- **Sentiment merge index-safe** — replaced `df.join()` (which could silently misalign rows on duplicate dates) with a date-string map, preserving the original DatetimeIndex exactly.
- **Feature count guard at inference** — `prepare_inference_data` now raises a clear `ValueError` if the scaler's expected feature count doesn't match the inference DataFrame.
- **`dropna` scoped to feature columns** — `dropna(subset=feature_cols)` replaces `dropna()` so the `source` string column can't silently trigger row drops.

### API & Backend
- **Lifespan pre-warm** — all 5 models are loaded into memory at startup via the FastAPI `lifespan` handler. The first user request is never a cold model load.
- **LRU model cache (5 slots)** — `K.clear_session()` removed; eviction now drops only the oldest model without invalidating other cached models.
- **`CachedPrediction` DB table** — new SQLAlchemy model storing pre-computed forecasts per coin, with staleness check (`PREDICTION_STALE_HOURS`).
- **Admin endpoints** — `POST /admin/predictions/refresh` (all coins, background task) and `POST /admin/predictions/refresh/{coin}` (single coin, synchronous), both protected by `X-API-Key`.
- **`/validate/{coin}` cached** — backtest results are cached for 24h (`REDIS_VALIDATION_TTL`); the endpoint is lazy-loaded only when the user opens the Accuracy panel.
- **Debug endpoints gated** — `/debug/*` routes now return 403 in production (`DEBUG=false`).
- **GZip middleware** — responses > 1KB are automatically compressed.
- **`render.yaml` upgraded** — plan changed from `free` to `starter`; worker service replaced with a static site for the frontend; all env vars declared with `sync: false`.

### CI/CD & Local Trainer
- **`local_train.py` restructured** — 3 explicit steps (clear cache → train → pre-compute predictions) with coloured output, pre-flight data availability check, and non-swallowable errors (exits with code 1 on failure).
- **`daily_train.yml` split into 2 jobs** — `train` (runs `local_train.py` with Supabase secrets) and `refresh-predictions` (calls `/admin/predictions/refresh` and verifies all 5 coins updated). Manual trigger supports `skip_training` and per-coin inputs.
- **Test workflow hardened** — `PYTHONPATH`, `USE_S3=false`, `USE_POSTGRES=false`, `USE_REDIS=false` set as job-level env vars; `pytest -v --tb=short` for clearer CI output; `develop` branch added to push triggers.
- **SQLAlchemy 2.x** — migrated from `declarative_base()` to `DeclarativeBase`; all `DateTime` columns use `timezone=True`.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Layer 1 — Training Pipeline  (once daily, offline)      │
│  GitHub Actions → local_train.py                         │
│  Fetch candles → Train LSTM-CNN → Upload to Supabase S3  │
│  Pre-compute predictions → Write to cached_predictions   │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────┐
│  Layer 2 — FastAPI Backend  (Render Starter)             │
│  Startup: all 5 models loaded into RAM (pre-warm)        │
│  POST /predict/{coin}                                    │
│    1. Redis cache         →  ~5 ms                       │
│    2. DB prediction store → ~80 ms                       │
│    3. Live LSTM inference → ~800 ms  (fallback)          │
│  GET /market-data/{coin}  → Redis 5-min TTL → CCXT       │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────┐
│  Layer 3 — React Frontend  (Render Static)               │
│  • Market data loads first (chart appears instantly)     │
│  • Cached prediction loads next (~80 ms)                 │
│  • Validation panel lazy-loads only when opened          │
│  • Binance WebSocket for live price ticker               │
└──────────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Details |
|---|---|
| **Parallel LSTM-CNN** | LSTM and CNN branches run in parallel — both see the full raw sequence. LSTM captures long-range trends; CNN captures local volatility spikes. Merged before the forecast head. |
| **Monte Carlo Dropout** | N stochastic forward passes with `training=True`. `n=5` for user requests, `n=20` for the daily batch. Reports mean ± 90% confidence bounds. |
| **3-tier prediction cache** | Redis → DB store → live inference. Typical response < 100ms. |
| **15-feature engineering** | RSI (Wilder's), MACD×3, EMA×3 (7/25/50), ATR, vol_ma_20, OHLCV, Fear & Greed sentiment. |
| **Live WebSocket prices** | Binance `@ticker` stream — no polling, no API key. |
| **Lazy validation panel** | 30-day rolling backtest only runs when user opens the Accuracy panel. Results cached 24h. |
| **PSI drift detection** | Population Stability Index compares training vs serving feature distributions. |
| **Admin API** | `POST /admin/predictions/refresh` (requires `X-API-Key`) triggers a full prediction batch. |
| **Pre-warm startup** | All 5 models loaded into RAM at FastAPI startup; no cold-load on first request. |

---

## Tech Stack

**Backend:** Python 3.11, FastAPI, TensorFlow-CPU, scikit-learn, SQLAlchemy 2.x, Redis, CCXT, boto3

**Frontend:** React 19, Vite 7, Tailwind CSS 4, Recharts, Framer Motion, TensorFlow.js

**Infrastructure:** Render (API + Static Frontend), Supabase (PostgreSQL + S3), Upstash (Redis), GitHub Actions (CI/CD)

---

## Getting Started

### Prerequisites

- Python 3.11 or 3.12
- Node.js 18+

### Local Development

```bash
# 1. Clone and set up Python environment
git clone https://github.com/AaravKashyap12/CryptoQuant.git
cd CryptoQuant
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — for local dev leave USE_S3/USE_POSTGRES/USE_REDIS=false

# 3. Start the API
export PYTHONPATH=$(pwd)        # Windows: set PYTHONPATH=%CD%
uvicorn services.api.main:app --host 0.0.0.0 --port 8002 --reload

# 4. Start the frontend (separate terminal)
cd frontend
npm install
npm run dev                     # opens http://localhost:3000
```

> **No models yet?** Run `python local_train.py` first to train and register models locally.

---

## Training Models

```bash
# macOS / Linux
source venv/bin/activate
export PYTHONPATH=$(pwd)
python local_train.py

# Windows
train_models.bat
```

**What the pipeline does (3 steps):**
1. Pre-flight data availability check per coin
2. Trains Hybrid LSTM-CNN for all 5 coins (fetches up to 2000 candles each, engineers 15 features, 80/20 chronological split)
3. Pre-computes n_iter=20 MC Dropout forecasts and writes to `cached_predictions` table

---

## Deployment

### Backend (Render Starter)

`render.yaml` is pre-configured. Set the following secrets in the Render dashboard (not in the file — they're marked `sync: false`):

```
DB_URL          → Supabase PostgreSQL connection string
S3_ENDPOINT_URL → https://<ref>.supabase.co/storage/v1/s3
S3_ACCESS_KEY   → Supabase S3 access key
S3_SECRET_KEY   → Supabase S3 secret key
REDIS_URL       → Upstash Redis URL
ADMIN_API_KEY   → Secret key for /admin/* endpoints
```

### Frontend (Render Static — included in render.yaml)

Set `VITE_API_URL` to your Render backend URL during build. SPA routing is handled by the rewrite rule in `render.yaml`.

### Redis (Upstash)

Create a free Redis database at [upstash.com](https://upstash.com), copy the URL, and set `REDIS_URL` + `USE_REDIS=true` in your backend environment.

---

## GitHub Actions Secrets

| Secret | Required for |
|---|---|
| `SUPABASE_DB_URL` | Model version registration |
| `SUPABASE_S3_ENDPOINT` | Artifact upload |
| `SUPABASE_S3_ACCESS_KEY` | Artifact upload |
| `SUPABASE_S3_SECRET_KEY` | Artifact upload |
| `S3_BUCKET_NAME` | Artifact upload |
| `API_BASE_URL` | Prediction refresh trigger |
| `ADMIN_API_KEY` | Protecting `/admin/*` endpoints |
| `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` | `publish.yml` only |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `USE_S3` | `false` | Supabase S3 artifact storage |
| `USE_POSTGRES` | `false` | PostgreSQL instead of SQLite |
| `USE_REDIS` | `false` | Redis cache layer |
| `DEBUG` | `true` | Expose `/debug/*` endpoints — set `false` in prod |
| `DB_URL` | sqlite | PostgreSQL connection string |
| `REDIS_URL` | localhost | Redis URL |
| `REDIS_PREDICTION_TTL` | `3600` | Prediction cache TTL (s) |
| `REDIS_OHLCV_TTL` | `300` | OHLCV cache TTL (s) |
| `REDIS_VALIDATION_TTL` | `86400` | Validation cache TTL (s) |
| `PREDICTION_STALE_HOURS` | `24` | Hours before a DB prediction is considered stale |
| `ADMIN_API_KEY` | `""` | Header key for `/admin/*`; empty = unprotected (dev only) |

---

## Project Structure

```
CryptoQuant/
├── local_train.py          # Run locally to train + push models (3-step pipeline)
├── train_models.bat        # Windows launcher
├── .env.example            # Backend env variable template
│
├── services/api/
│   ├── main.py             # FastAPI app + lifespan pre-warm
│   ├── Dockerfile
│   ├── requirements.txt
│   └── routes/endpoints.py # Public + admin + debug endpoints
│
├── shared/
│   ├── core/config.py      # All settings (Pydantic BaseSettings)
│   └── ml/
│       ├── cache.py        # Redis / in-process cache (auto-selects)
│       ├── evaluate.py     # Rolling backtest (MC Dropout) + offline metrics
│       ├── models.py       # build_model (parallel LSTM+CNN), build_hybrid_model
│       ├── monitoring.py   # PSI drift detection + prediction logging
│       ├── predict.py      # MC Dropout inference + daily batch + tf.function cache
│       ├── registry.py     # ModelRegistry + CachedPrediction store + LRU cache
│       ├── storage.py      # S3 / Local artifact store
│       └── training.py     # Full training pipeline (COIN_CONFIG per-coin limits)
│   └── utils/
│       ├── data_fetcher.py # Multi-exchange OHLCV (per-symbol priority) + sentiment
│       ├── features.py     # Technical indicators (Wilder RSI, ema_50, centralised dropna)
│       └── preprocess.py   # Training + inference data prep (feature guard, scoped dropna)
│
├── tests/unit/
│   ├── test_registry.py
│   ├── test_preprocess.py
│   └── test_monitoring.py
│
└── .github/workflows/
    ├── test.yml            # pytest on every push/PR (USE_S3/POSTGRES/REDIS=false)
    ├── daily_train.yml     # 2-job pipeline: train models + refresh predictions (01:00 UTC)
    └── publish.yml         # Docker Hub publish on tag push
```

---

## How Predictions Work

1. **Daily at 01:00 UTC** — GitHub Actions runs `local_train.py`. After training, it calls `run_prediction_batch(n_iter=20)` which runs 20 stochastic MC Dropout passes per coin and writes results to `cached_predictions`.

2. **User hits `/predict/BTC`:**
   - Redis has it → returned immediately (~5ms)
   - DB has a fresh row → returned, Redis warmed (~80ms)
   - Neither → live inference runs, result stored in DB + Redis (~800ms, rare)

3. **Confidence bands** — 5th and 95th percentiles of 20 MC Dropout samples form the lower/upper bounds.

4. **Validation panel** — walk-forward backtest comparing predicted `close[i+1]` against actual `close[i+1]`. Results cached 24h. Only triggered when the user clicks "Show Model Accuracy".

---

## Disclaimer

**NOT FINANCIAL ADVICE.** All predictions are for educational purposes only. Cryptocurrency markets are highly volatile. Do not trade based solely on these outputs.

---

Made by [Aarav Kashyap](https://x.com/KashyapAarav_)