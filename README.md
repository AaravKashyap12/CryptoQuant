<div align="center">

  <img src="frontend/public/vite.svg" alt="logo" width="100" height="auto" />
  <h1>CryptoQuant Analytics</h1>
  
  <p>
    An advanced cryptocurrency price forecasting tool powered by LSTM neural networks.
  </p>
  
<!-- Badges -->
<p>
  <a href="https://github.com/AaravKashyap12/CryptoQuant/graphs/contributors">
    <img src="https://img.shields.io/github/contributors/AaravKashyap12/CryptoQuant" alt="contributors" />
  </a>
  <a href="https://github.com/AaravKashyap12/CryptoQuant/network/members">
    <img src="https://img.shields.io/github/forks/AaravKashyap12/CryptoQuant" alt="forks" />
  </a>
  <a href="https://github.com/AaravKashyap12/CryptoQuant/stargazers">
    <img src="https://img.shields.io/github/stars/AaravKashyap12/CryptoQuant" alt="stars" />
  </a>
</p>
   
<h4>
    <a href="https://cryptoquant.vercel.app">View Demo</a>
  <span> · </span>
    <a href="https://github.com/AaravKashyap12/CryptoQuant/issues/">Report Bug</a>
  </h4>
</div>

<br />

# :notebook_with_decorative_cover: Table of Contents

- [About the Project](#star2-about-the-project)
  - [Tech Stack](#space_invader-tech-stack)
  - [Production Architecture](#building_construction-production-architecture)
- [Getting Started](#toolbox-getting-started)
  - [Prerequisites](#bangbang-prerequisites)
  - [Local Training Flow](#brain-local-training-flow)
- [Deployment](#rocket-deployment)
- [Usage](#eyes-usage)

## :star2: About the Project

**CryptoQuant** is a quantitative forecasting dashboard that uses LSTM neural networks to predict cryptocurrency price movements. It fetches real-time data from Binance and provides specialized metrics like volatility spread and forecast uncertainty.

### :space_invader: Tech Stack
- **Frontend**: React.js, TailwindCSS, Framer Motion, Recharts.
- **Backend API**: FastAPI, TensorFlow (CPU-optimized), SQLAlchemy.
- **Infrastructure**: Supabase (PostgreSQL + S3 Storage), Render (API), Vercel (Frontend).

### :building_construction: Production Architecture
To bypass cloud memory limits (512MB RAM), we use a **Local-to-Cloud** architecture:
1. **Local Utility**: Train models on your hardware using `local_train.py`.
2. **Cloud Storage**: Models and metadata are pushed directly to **Supabase**.
3. **Live API**: The Render backend loads the latest models from the cloud registry for instance inference.

## :toolbox: Getting Started

### :bangbang: Prerequisites
- **Python**: v3.11 or v3.12 (TensorFlow compatibility)
- **Node.js**: v18+

### :brain: Local Training Flow
Since training requires ~1.5GB of RAM, it is recommended to run it locally:

1. Setup your `.env` with Supabase credentials.
2. Install requirements: `pip install -r services/api/requirements.txt`.
3. Run the trainer:
   ```bash
   python local_train.py
   ```
4. This script fetches market data, trains the LSTM, and pushes artifacts to your production cloud.

## :rocket: Deployment

### 1. Backend (Render)
- **Root Directory**: `.`
- **Build Command**: `pip install -r services/api/requirements.txt`
- **Start Command**: `uvicorn services.api.main:app --host 0.0.0.0 --port $PORT`

### 2. Frontend (Vercel)
- **Root Directory**: `frontend`
- **VITE_API_URL**: `https://your-api.onrender.com`

## :eyes: Usage
- **Forecast**: View the 7-day price projection with dynamic confidence intervals.
- **Accuracy**: Scroll down to the **Model Accuracy** chart to see historical backtest records.
- **Metrics**: Monitor real-time price trends and forecast uncertainty spreads.

---
Aarav Kashyap - [@KashyapAarav_](https://x.com/KashyapAarav_)
