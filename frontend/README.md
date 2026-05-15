# CryptoQuant Frontend

Pure Vite + React dashboard. There is no local API server.

```bash
npm install
npm run dev
```

Data sources:

- Binance REST daily candles
- Binance WebSocket live ticker
- alternative.me Fear & Greed Index
- CoinGecko public market data
- Optional TF.js models from `public/models/<COIN>/model.json`

If a TF.js model is not present, the app falls back to a browser-side statistical forecast.

From the repo root, use `train_models.bat` to refresh local model files only, or `train_and_push.bat` to train, commit `frontend/public/models`, and push for Vercel redeploy.
