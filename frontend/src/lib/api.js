import axios from 'axios';

/**
 * API client for CryptoQuant backend.
 *
 * URL resolution (in priority order):
 *  1. VITE_API_URL env var — set in Vercel dashboard for production, or .env.local for dev override
 *  2. Relative /api/v1 — works automatically with the Vite dev proxy (vite.config.js)
 *
 * The Vite proxy forwards /api/* → localhost:8001 in development, so you
 * don't need VITE_API_URL set at all for normal local development.
 */
function resolveBaseURL() {
  const explicit = import.meta.env.VITE_API_URL;
  if (explicit) {
    const base = explicit.replace(/\/$/, '');
    return base.endsWith('/api/v1') ? base : `${base}/api/v1`;
  }
  // Dev: relative path — Vite proxy handles the forwarding
  return '/api/v1';
}

const api = axios.create({
  baseURL: resolveBaseURL(),
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,  // 30 s — reduce to 10 000 once on paid infra (no cold starts)
});

// ── Response interceptor — consistent error logging ───────────────────────────
api.interceptors.response.use(
  res => res,
  err => {
    const status = err.response?.status;
    if (status === 401) console.error('[API] Unauthorized — check ADMIN_API_KEY');
    if (status === 404) console.warn('[API] 404 Not Found:', err.config?.url);
    if (!err.response)  console.error('[API] Network error — is the backend running?');
    return Promise.reject(err);
  }
);

// ── Endpoints ─────────────────────────────────────────────────────────────────
export const getCoins = async () => {
  const res = await api.get('/coins');
  return res.data;
};

export const getMarketData = async (coin, limit = 100) => {
  try {
    const res = await api.get(`/market-data/${coin}`, { params: { limit } });
    return res.data;
  } catch (error) {
    console.error('Market data error:', error);
    return [];
  }
};

export const getPrediction = async (coin) => {
  const res = await api.post(`/predict/${coin}`);
  return res.data;
};

export const getMetrics = async (coin) => {
  const res = await api.get(`/metrics/${coin}`);
  return res.data;
};

export const getValidation = async (coin, days = 30) => {
  const res = await api.get(`/validate/${coin}`, { params: { days } });
  return res.data;
};

export default api;
