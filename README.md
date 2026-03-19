<div align="center">

<img src="frontend/public/cryptoquant_favicon.svg" alt="CryptoQuant Logo" width="80" height="80" />

# CryptoQuant

**Quantitative Analytics Terminal**

A full-stack cryptocurrency forecasting platform powered by a Hybrid LSTM–CNN ensemble, Monte Carlo Dropout uncertainty estimation, and a 3-tier Redis-backed prediction cache.

[![Tests](https://github.com/AaravKashyap12/CryptoQuant/actions/workflows/test.yml/badge.svg)](https://github.com/AaravKashyap12/CryptoQuant/actions/workflows/test.yml)
[![Stars](https://img.shields.io/github/stars/AaravKashyap12/CryptoQuant)](https://github.com/AaravKashyap12/CryptoQuant/stargazers)
[![Contributors](https://img.shields.io/github/contributors/AaravKashyap12/CryptoQuant)](https://github.com/AaravKashyap12/CryptoQuant/graphs/contributors)

[**Live Demo**](https://cryptoquant.vercel.app) · [**Report Bug**](https://github.com/AaravKashyap12/CryptoQuant/issues)

</div>

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  EXTERNAL SOURCES                                               │
│  CCXT Exchanges (Kraken · KuCoin · Coinbase · OKX · Binance)   │
│  alternative.me Fear & Greed Index · Binance WebSocket          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  LAYER 1 — TRAINING PIPELINE  (local machine → Supabase)        │
│                                                                  │
│  data_fetcher ──► features.py ──► models.py ──► local_train.py  │
│  OHLCV+sentiment   15 features    LSTM ‖ CNN    train→upload     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  LAYER 2 — SUPABASE CLOUD STORAGE                               │
│                                                                  │
│  ┌────────────────┐  ┌──────────────────────┐  ┌─────────────┐ │
│  │   S3 Bucket    │  │     PostgreSQL        │  │Upstash Redis│ │
│  │ .keras · .pkl  │  │ model_versions        │  │pred: 1h TTL │ │
│  │ tfjs artifacts │  │ cached_predictions    │  │ohlcv: 5m TTL│ │
│  └────────────────┘  └──────────────────────┘  └─────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  LAYER 3 — FASTAPI BACKEND  (Render Starter · pre-warmed)       │
│                                                                  │
│  POST /predict/{coin}    ┌─────────────────────────────────┐    │
│  ├── Tier 1: Redis  ─────│         ~5 ms                   │    │
│  ├── Tier 2: DB     ─────│        ~80 ms                   │    │
│  └── Tier 3: Infer  ─────│       ~800 ms  (fallback only)  │    │
│                           └─────────────────────────────────┘    │
│  ⏱  cron-job.org pings /health every 10 min — zero cold starts  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  LAYER 4 — REACT FRONTEND  (Vercel)                             │
│                                                                  │
│  PriceChart · useLivePrice (Binance WS) · ValidationChart       │
│  ModelExplainer · CoinSelector · 7-day forecast strip           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Details |
|---|---|
| **Parallel LSTM-CNN** | LSTM and CNN run in parallel on the same raw input sequence. LSTM captures long-range trends; CNN captures local volatility spikes. |
| **Monte Carlo Dropout** | 20 stochastic forward passes at batch time, 5 for user requests. Reports mean ± 90% confidence bounds. |
| **3-tier prediction cache** | Redis → DB store → live inference. Typical response < 100ms. |
| **Zero cold starts** | cron-job.org pings `/health` every 10 minutes keeping the server warm 24/7. |
| **15-feature engineering** | Wilder RSI, MACD×3, EMA×3 (7/25/50), ATR, vol_ma_20, OHLCV, Fear & Greed sentiment. |
| **Live WebSocket prices** | Binance `@ticker` stream — no polling, no API key required. |
| **Lazy validation panel** | 30-day walk-forward backtest only runs when user opens the Accuracy panel. Results cached 24h. |
| **Pre-warm startup** | All 5 models loaded into RAM at FastAPI startup. No cold model load on first request. |
| **Admin API** | `POST /admin/predictions/refresh` protected by `X-API-Key` triggers a full prediction batch. |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **ML & Backend** | Python 3.11 · TensorFlow-CPU · FastAPI · SQLAlchemy 2.x · CCXT · boto3 |
| **Databases** | Supabase PostgreSQL · Supabase S3 · Upstash Redis |
| **Frontend** | React 19 · Vite · Tailwind CSS · Recharts · Framer Motion · IBM Plex Mono |
| **Infrastructure** | Render · Vercel · GitHub Actions · cron-job.org |

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
# For local dev set USE_S3=false USE_POSTGRES=false USE_REDIS=false

# 3. Start the API
export PYTHONPATH=$(pwd)        # Windows: set PYTHONPATH=%CD%
uvicorn services.api.main:app --host 0.0.0.0 --port 8002 --reload

# 4. Start the frontend (separate terminal)
cd frontend && npm install && npm run dev
```

> **No models yet?** Run `python local_train.py` first to train and register models locally.

---

## Training Models

```bash
# macOS / Linux
source venv/bin/activate && export PYTHONPATH=$(pwd)
python local_train.py

# Windows
train_models.bat
```

**3-step pipeline:**

1. **Pre-flight** — verifies each coin has sufficient data rows before training starts
2. **Train** — fetches up to 2000 candles per coin, engineers 15 features, 80/20 chronological split, trains Hybrid LSTM-CNN, uploads `.keras` + scalers to Supabase S3, registers version in PostgreSQL
3. **Pre-compute** — runs n_iter=20 MC Dropout forecasts for all 5 coins, writes to `cached_predictions` table so the API serves instantly

---

## Deployment

### Backend — Render Starter

Set in Render dashboard → Environment (not in `render.yaml` — keep secrets out of git):

```
DB_URL            → Supabase PostgreSQL connection string
S3_ENDPOINT_URL   → https://<ref>.supabase.co/storage/v1/s3
S3_ACCESS_KEY     → Supabase S3 access key
S3_SECRET_KEY     → Supabase S3 secret key
S3_BUCKET_NAME    → models
REDIS_URL         → rediss://your-upstash-url
ADMIN_API_KEY     → any secret string
DEBUG             → false
```

### Frontend — Vercel

Set `VITE_API_URL` to your Render API URL in Vercel dashboard → Settings → Environment Variables.

### Cold Start Prevention

Create a free job at [cron-job.org](https://cron-job.org) → URL: `https://your-api.onrender.com/health` → every 10 minutes. Keeps server warm 24/7 at zero cost.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `USE_S3` | `false` | Supabase S3 artifact storage |
| `USE_POSTGRES` | `false` | PostgreSQL instead of SQLite |
| `USE_REDIS` | `false` | Redis cache layer |
| `DEBUG` | `true` | Expose `/debug/*` — set `false` in prod |
| `REDIS_PREDICTION_TTL` | `3600` | Prediction cache TTL (seconds) |
| `REDIS_OHLCV_TTL` | `300` | OHLCV cache TTL (seconds) |
| `REDIS_VALIDATION_TTL` | `86400` | Validation cache TTL (seconds) |
| `PREDICTION_STALE_HOURS` | `24` | Hours before DB prediction is considered stale |
| `ADMIN_API_KEY` | `""` | Header key for `/admin/*` endpoints |

---

## Project Structure

```
CryptoQuant/
├── local_train.py              # Train + push models (3-step pipeline)
├── train_models.bat            # Windows launcher
├── .env.example                # Environment variable template
│
├── services/api/
│   ├── main.py                 # FastAPI app + lifespan pre-warm
│   └── routes/endpoints.py    # Public + admin + debug endpoints
│
├── shared/
│   ├── core/config.py          # Pydantic BaseSettings
│   └── ml/
│       ├── cache.py            # Redis / in-process cache (auto-selects)
│       ├── evaluate.py         # Rolling backtest + MC Dropout metrics
│       ├── models.py           # build_model — parallel LSTM + CNN
│       ├── monitoring.py       # PSI drift detection
│       ├── predict.py          # MC Dropout inference + batch job
│       ├── registry.py         # ModelRegistry + LRU cache + CachedPrediction
│       ├── storage.py          # S3 / Local artifact store (Strategy pattern)
│       └── training.py         # Training pipeline + per-coin COIN_CONFIG
│   └── utils/
│       ├── data_fetcher.py     # Multi-exchange OHLCV + sentiment (2-tier cache)
│       ├── features.py         # Wilder RSI · MACD · EMA · ATR · sentiment merge
│       └── preprocess.py       # Training + inference data prep + feature guards
│
├── frontend/src/
│   ├── App.jsx                 # Main shell + sequential data loading
│   ├── components/             # CoinSelector · PriceChart · MetricsCard · ...
│   ├── hooks/useLivePrice.js   # Binance WebSocket live price hook
│   └── lib/api.js              # Axios client + typed endpoint functions
│
├── tests/unit/
│   ├── test_registry.py        # Registry · LRU cache · version increment
│   ├── test_preprocess.py      # Feature engineering shape tests
│   └── test_monitoring.py      # PSI drift detection tests
│
└── .github/workflows/
    ├── test.yml                # pytest on every push/PR
    ├── daily_train.yml         # Daily retrain + prediction refresh (01:00 UTC)
    └── publish.yml             # Docker Hub publish on tag push
```

---

## How Predictions Work

1. **Daily** — `local_train.py` trains all 5 coin models locally, uploads to Supabase, pre-computes n_iter=20 forecasts, writes to `cached_predictions`.

2. **User hits `/predict/BTC`:**
   - Redis hit → ~5ms
   - DB hit → ~80ms, Redis warmed
   - Cache miss → live inference ~800ms, result cached in DB + Redis

3. **Confidence bands** — 5th and 95th percentiles of MC Dropout passes.

4. **Validation panel** — walk-forward backtest comparing `predicted[i+1]` vs `actual[i+1]`. Cached 24h. Lazy — only runs on user request.

5. **Cold starts** — cron-job.org pings `/health` every 10 minutes. Server never idles.

---

## Disclaimer

**NOT FINANCIAL ADVICE.** All predictions are for educational and research purposes only. Do not make trading decisions based solely on these outputs.

---

<div align="center">
  Made by <a href="https://x.com/KashyapAarav_">Aarav Kashyap</a>
</div>