import { buildFeatureMatrix, runEdgeInference } from './inference.js';

const SUPPORTED_COINS = ['BTC', 'ETH', 'BNB', 'SOL', 'ADA'];

const COIN_IDS = {
  BTC: 'bitcoin',
  ETH: 'ethereum',
  BNB: 'binancecoin',
  SOL: 'solana',
  ADA: 'cardano',
};

export const PUBLIC_API_CACHE_MS = 60_000;
const publicApiCache = new Map();

export function clearPublicApiCache() {
  publicApiCache.clear();
}

export const fetchJson = async (url, options = {}) => {
  const now = options.now?.() ?? Date.now();
  const cached = publicApiCache.get(url);
  if (cached && now - cached.timestamp < PUBLIC_API_CACHE_MS) {
    return cached.data;
  }

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed ${response.status}: ${url}`);
  }
  const data = await response.json();
  publicApiCache.set(url, { data, timestamp: now });
  return data;
};

const toNumber = (value, fallback = 0) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

function rollingRsi(candles, period = 14) {
  if (!candles.length) return [];

  const closes = candles.map(candle => candle.close);
  const result = Array(candles.length).fill(50);
  const deltas = closes.slice(1).map((value, index) => value - closes[index]);
  if (deltas.length < period) return result;

  const gains = deltas.map(delta => (delta > 0 ? delta : 0));
  const losses = deltas.map(delta => (delta < 0 ? -delta : 0));
  let avgGain = gains.slice(0, period).reduce((total, value) => total + value, 0) / period;
  let avgLoss = losses.slice(0, period).reduce((total, value) => total + value, 0) / period;
  result[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);

  for (let i = period + 1; i < closes.length; i += 1) {
    avgGain = avgGain * (1 - 1 / period) + gains[i - 1] * (1 / period);
    avgLoss = avgLoss * (1 - 1 / period) + losses[i - 1] * (1 / period);
    result[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }

  return result;
}

function dailyReturns(candles) {
  return candles.slice(1)
    .map((candle, index) => {
      const previous = candles[index]?.close;
      return previous ? (candle.close - previous) / previous : 0;
    })
    .filter(Number.isFinite);
}

function mean(values) {
  if (!values.length) return 0;
  return values.reduce((total, value) => total + value, 0) / values.length;
}

function standardDeviation(values) {
  if (values.length < 2) return 0;
  const avg = mean(values);
  const variance = mean(values.map(value => (value - avg) ** 2));
  return Math.sqrt(variance);
}

function nextDayIsoDate(openTime) {
  const date = new Date(Number(openTime));
  date.setUTCDate(date.getUTCDate() + 1);
  return date.toISOString().slice(0, 10);
}

export const getCoins = async () => SUPPORTED_COINS;

export function normalizeBinanceKlines(rows) {
  const candles = rows.map(row => ({
    open_time: toNumber(row[0]),
    open: toNumber(row[1]),
    high: toNumber(row[2]),
    low: toNumber(row[3]),
    close: toNumber(row[4]),
    volume: toNumber(row[5]),
  }));

  const rsiValues = rollingRsi(candles);
  return candles.map((candle, index) => ({
    ...candle,
    rsi: rsiValues[index] ?? 50,
  }));
}

export const getMarketData = async (coin, limit = 200) => {
  try {
    const symbol = `${String(coin).toUpperCase()}USDT`;
    const rows = await fetchJson(
      `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=1d&limit=${limit}`
    );
    return normalizeBinanceKlines(rows);
  } catch (error) {
    console.error('[PublicData] Market data error:', error);
    return [];
  }
};

export function buildBaselinePrediction(coin, candles, source = 'statistical_baseline') {
  if (!candles?.length) return null;

  const latest = candles[candles.length - 1];
  const recentReturns = dailyReturns(candles).slice(-30);
  const averageReturn = clamp(mean(recentReturns), -0.05, 0.05);
  const volatility = clamp(standardDeviation(recentReturns), 0.005, 0.2);
  const predicted = latest.close * (1 + averageReturn);
  const bandWidth = Math.max(latest.close * volatility * 1.65, latest.close * 0.01);

  return {
    coin,
    computed_at: new Date().toISOString(),
    from_cache: false,
    forecast: {
      dates: [nextDayIsoDate(latest.open_time)],
      mean: [predicted],
      upper: [predicted + bandWidth],
      lower: [Math.max(predicted - bandWidth, 0)],
    },
    metadata: {
      serving_mode: source === 'edge_model'
        ? 'browser TF.js model'
        : 'browser statistical baseline',
      mc_iterations: 1,
      eligible_for_cached_serving: true,
      metrics: {
        last_close: latest.close,
        realized_volatility_30d: volatility,
      },
    },
  };
}

export const getPrediction = async (coin) => {
  const candles = await getMarketData(coin, 220);
  if (!candles.length) return null;

  try {
    const sentiment = await getSentiment().catch(() => null);
    const sentimentScore = sentiment?.sentiment_score ?? 50;
    const inputMatrix = buildFeatureMatrix(candles, 60, sentimentScore);
    const output = inputMatrix ? await runEdgeInference(coin, inputMatrix) : null;
    const predicted = Array.isArray(output) ? toNumber(output[0], NaN) : NaN;
    const latest = candles[candles.length - 1].close;
    const plausiblePrediction = Number.isFinite(predicted)
      && predicted > latest * 0.2
      && predicted < latest * 5;

    if (plausiblePrediction) {
      const modelPrediction = buildBaselinePrediction(coin, candles, 'edge_model');
      modelPrediction.forecast.mean[0] = predicted;
      const recentVolatility = clamp(standardDeviation(dailyReturns(candles).slice(-30)), 0.005, 0.2);
      const bandWidth = Math.max(predicted * recentVolatility * 1.65, predicted * 0.01);
      modelPrediction.forecast.upper[0] = predicted + bandWidth;
      modelPrediction.forecast.lower[0] = Math.max(predicted - bandWidth, 0);
      return modelPrediction;
    }
  } catch (error) {
    console.warn('[PublicData] Edge inference unavailable, using baseline:', error);
  }

  return buildBaselinePrediction(coin, candles);
};

export const getMetrics = async (coin) => {
  const candles = await getMarketData(coin, 120);
  const prediction = buildBaselinePrediction(coin, candles);
  return prediction?.metadata?.metrics || {};
};

export function buildValidationSeries(candles, days = 30) {
  if (!Array.isArray(candles) || candles.length < 35) return [];

  return candles.slice(-days).map((candle, index, window) => {
    const absoluteIndex = candles.length - days + index;
    const history = candles.slice(Math.max(0, absoluteIndex - 21), absoluteIndex);
    const returns = dailyReturns(history);
    const averageReturn = clamp(mean(returns), -0.05, 0.05);
    const previousClose = candles[absoluteIndex - 1]?.close ?? window[index - 1]?.close ?? candle.close;

    return {
      date: new Date(Number(candle.open_time)).toISOString().slice(0, 10),
      actual: candle.close,
      predicted: previousClose * (1 + averageReturn),
    };
  });
}

export const getValidation = async (coin, days = 30) => {
  try {
    const candles = await getMarketData(coin, Math.max(days + 80, 120));
    const validation = buildValidationSeries(candles, days);
    return validation.length ? validation : { error: 'VALIDATION UNAVAILABLE' };
  } catch (error) {
    return {
      error: error.message || 'VALIDATION UNAVAILABLE',
    };
  }
};

export const getSentiment = async () => {
  const data = await fetchJson('https://api.alternative.me/fng/?limit=1');
  const latest = data?.data?.[0];
  const score = toNumber(latest?.value, 50);

  return {
    status: 'live',
    provider: 'alternative.me',
    sentiment_score: score,
    value: score,
    label: latest?.value_classification || 'Neutral',
    updated_at: latest?.timestamp
      ? new Date(Number(latest.timestamp) * 1000).toISOString()
      : new Date().toISOString(),
  };
};

export const getOnChainSignals = async (coin) => {
  const symbol = String(coin).toUpperCase();
  const id = COIN_IDS[symbol] || 'bitcoin';
  const data = await fetchJson(
    `https://api.coingecko.com/api/v3/coins/${id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false`
  );
  const market = data?.market_data || {};
  const usdVolume = toNumber(market.total_volume?.usd, NaN);
  const usdMarketCap = toNumber(market.market_cap?.usd, NaN);
  const change24h = toNumber(market.price_change_percentage_24h, NaN);

  return {
    status: 'live',
    provider: 'coingecko-public',
    updated_at: data?.last_updated || new Date().toISOString(),
    signals: {
      volume_24h: {
        value: usdVolume,
        unit: 'USD',
        description: 'CoinGecko spot volume',
        change_7d_pct: toNumber(market.price_change_percentage_7d, NaN),
      },
      open_interest_usd: {
        value: usdMarketCap,
        unit: 'USD',
        description: 'Market cap proxy',
      },
      funding_rate: {
        value: change24h,
        unit: 'percent',
        description: '24h spot change',
      },
    },
  };
};

export default {
  getCoins,
  getMarketData,
  getPrediction,
  getMetrics,
  getValidation,
  getSentiment,
  getOnChainSignals,
};
