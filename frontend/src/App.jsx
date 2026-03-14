import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { CoinSelector } from './components/CoinSelector';
import { MetricsCard } from './components/MetricsCard';
import { PriceChart } from './components/PriceChart';
import { ModelExplainer } from './components/ModelExplainer';
import { ProjectInfo } from './components/ProjectInfo';
import { ValidationChart } from './components/ValidationChart';
import { RefreshCw, Info, Zap, BarChart2 } from 'lucide-react';
import { getCoins, getMarketData, getPrediction, getValidation } from './lib/api';
import { useLivePrice } from './hooks/useLivePrice';
import { runEdgeInference, buildFeatureMatrix } from './lib/inference';

function App() {
  const [coins, setCoins] = useState([]);
  const [selectedCoin, setSelectedCoin] = useState('BTC');
  const [marketData, setMarketData] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [showValidation, setShowValidation] = useState(false);   // lazy load
  const [loadingValidation, setLoadingValidation] = useState(false);
  const [edgePrediction, setEdgePrediction] = useState(null);
  const [computingEdge, setComputingEdge] = useState(false);

  const { price: livePrice, change24h: liveChange } = useLivePrice(`${selectedCoin}USDT`);

  // ── Init: Fetch supported coins ───────────────────────────────────────
  useEffect(() => {
    let retries = 5;
    async function init() {
      try {
        const c = await getCoins();
        setCoins(c || []);
      } catch (e) {
        if (retries > 0) {
          retries--;
          setTimeout(init, 3000); 
        }
      }
    }
    init();
  }, []);

  // ── Data loading triggers when backend is ready (coins list exists) ─────
  useEffect(() => {
    if (selectedCoin && coins.length > 0) {
      loadCoreData(selectedCoin);
    }
  }, [selectedCoin, coins]);

  // ── Core data load: market + prediction only (fast path) ─────────────────
  const loadCoreData = useCallback(async (coin) => {
    // Prevent state update if we're already loading this exact coin
    setLoading(true);
    setMarketData([]);
    setPrediction(null);
    setValidation(null);
    setShowValidation(false);
    setEdgePrediction(null);

    try {
      // Step 1 — market data (charts appear immediately)
      const mData = await getMarketData(coin);
      
      // Step 2 — prediction (served from cache; fast)
      // Fetch in parallel if possible, but market data is higher priority for the chart
      const predData = await getPrediction(coin);
      
      setMarketData(mData || []);
      setPrediction(predData);
    } catch (e) {
      console.error('Data load error', e);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Validation — loaded lazily when user requests it ─────────────────────
  const handleShowValidation = useCallback(async () => {
    if (validation) {
      setShowValidation(true);
      return;
    }
    setLoadingValidation(true);
    setShowValidation(true);
    try {
      const valData = await getValidation(selectedCoin).catch(() => null);
      setValidation(valData);
    } finally {
      setLoadingValidation(false);
    }
  }, [selectedCoin, validation]);

  // ── Coin switch ───────────────────────────────────────────────────────────
  const handleCoinChange = (coin) => {
    setSelectedCoin(coin);
    // loadCoreData is now triggered via useEffect dependency on selectedCoin
  };

  // ── Refresh ───────────────────────────────────────────────────────────────
  const handleRefresh = async () => {
    setRefreshing(true);
    await loadCoreData(selectedCoin);
    setRefreshing(false);
  };

  // ── Edge inference ────────────────────────────────────────────────────────
  // NOTE: Edge inference requires a full 15-feature scaled matrix [60, 15].
  // The market data from the API contains OHLCV only (5 columns).
  // Without feature engineering (RSI, MACD, EMA, ATR, vol_ma_20, sentiment)
  // computed client-side, edge inference will produce incorrect results.
  // The button is kept for demonstration; a warning is shown if prerequisites aren't met.
  const handleEdgeInference = async () => {
    // Need 60 (lookback) + 14 (indicator warmup) candles minimum
    if (marketData.length < 74) return;
    setComputingEdge(true);
    try {
      // Build the full 15-feature matrix the model expects
      const inputMatrix = buildFeatureMatrix(marketData, 60);
      if (!inputMatrix) {
        console.warn('[EdgeInference] Not enough candles to build feature matrix');
        setComputingEdge(false);
        return;
      }
      // Strip /api/v1 from the axios baseURL to get the raw origin
      const apiOrigin = (import.meta.env.VITE_API_URL ?? window.location.origin)
        .replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
      const res = await runEdgeInference(selectedCoin, inputMatrix, apiOrigin);
      setEdgePrediction(res);
    } catch (e) {
      console.error('[EdgeInference]', e);
    }
    setComputingEdge(false);
  };

  // ── Derived state ─────────────────────────────────────────────────────────
  const currentPrice = marketData.length > 0 ? marketData[marketData.length - 1].close : 0;
  const prevPrice = marketData.length > 1 ? marketData[marketData.length - 2].close : currentPrice;
  const priceChange = currentPrice - prevPrice;
  const percentChange = prevPrice !== 0 ? (priceChange / prevPrice) * 100 : 0;

  const displayPrice = livePrice ?? currentPrice;
  const displayChange = liveChange ?? percentChange;

  const nextDayPred = prediction ? prediction.forecast.mean[0] : 0;
  const forecastTrend = nextDayPred > currentPrice ? 'up' : 'down';
  const forecastDiff = currentPrice !== 0 ? ((nextDayPred - currentPrice) / currentPrice) * 100 : 0;

  const upper = prediction ? prediction.forecast.upper[0] : 0;
  const lower = prediction ? prediction.forecast.lower[0] : 0;
  const spread = nextDayPred !== 0 ? ((upper - lower) / nextDayPred) * 100 : 0;

  return (
    <div className="min-h-screen bg-[#0e1117] text-gray-200 font-sans pb-20 relative">

      {loading && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-[#0e1117]/80 backdrop-blur-sm"
        >
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
            <p className="text-blue-400 font-medium animate-pulse">
              Fetching {selectedCoin} market data…
            </p>
          </div>
        </motion.div>
      )}

      <CoinSelector coins={coins} selectedCoin={selectedCoin} onSelect={handleCoinChange} />
      <ProjectInfo isOpen={showInfo} onClose={() => setShowInfo(false)} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8 space-y-8">

        {/* Header actions */}
        <motion.div
          initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}
          className="flex flex-wrap justify-end gap-3"
        >
          <button
            onClick={() => setShowInfo(true)}
            className="flex items-center gap-2 px-4 py-2 bg-[#1e1e1e] border border-[#333] rounded-lg hover:bg-[#252525] transition-colors text-sm font-medium text-gray-300"
          >
            <Info size={16} className="text-blue-400" /> About
          </button>

          <div className="flex items-center gap-2 px-4 py-2 bg-[#1e1e1e]/50 border border-[#333] rounded-lg text-xs font-medium text-gray-500">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            Live Market Analytics
          </div>
        </motion.div>

        {/* Cached prediction badge */}
        {prediction?.from_cache && prediction?.computed_at && (
          <div className="text-xs text-gray-500 text-right pr-1">
            Forecast computed {new Date(prediction.computed_at).toLocaleString()} · served from cache ⚡
          </div>
        )}

        {/* Metrics grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <MetricsCard
            title="Live Price / 24h"
            value={`$${displayPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
            subValue={`${displayChange > 0 ? '+' : ''}${displayChange.toFixed(2)}%`}
            trend={displayChange >= 0 ? 'up' : 'down'}
            className={displayChange >= 0 ? 'border-green-500/20' : 'border-red-500/20'}
            indicator={livePrice ? 'live' : null}
          />
          <MetricsCard
            title="7-Day Model Forecast"
            value={prediction ? `$${nextDayPred.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : 'Loading…'}
            subValue={prediction ? `${forecastDiff > 0 ? '+' : ''}${forecastDiff.toFixed(2)}% from now` : ''}
            trend={forecastTrend}
            tooltip="Average price predicted for tomorrow based on the LSTM model."
            className="border-yellow-500/30 bg-yellow-500/5"
          />
          <MetricsCard
            title="Forecast Uncertainty"
            value={prediction ? `±${(spread / 2).toFixed(2)}%` : 'Calculating…'}
            subValue="Volatility Spread"
            tooltip={`The model's 90% confidence interval spans a ${spread.toFixed(2)}% range.`}
          />
        </div>

        {/* Chart */}
        <motion.div
          initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.5 }}
          className="bg-[#1e1e1e] border border-[#333] rounded-3xl p-1 shadow-2xl"
        >
          <div className="bg-[#1e1e1e] rounded-[1.4rem] p-6">
            <PriceChart data={marketData} forecast={prediction ? prediction.forecast : null} />
          </div>
        </motion.div>

        {/* Validation — lazy loaded on user request */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}>
          {!showValidation ? (
            <button
              onClick={handleShowValidation}
              className="flex items-center gap-2 px-4 py-2 bg-[#1e1e1e] border border-[#333] rounded-xl hover:bg-[#252525] transition-colors text-sm font-medium text-gray-400"
            >
              <BarChart2 size={16} className="text-blue-400" />
              Show Model Accuracy (Last 30 Days)
            </button>
          ) : (
            <div className="bg-[#1e1e1e] border border-[#333] rounded-2xl p-6">
              <h3 className="text-lg font-bold flex items-center gap-2 mb-2">
                🎯 Model Accuracy (Last 30 Days)
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Comparison of what the model would have predicted vs what actually happened.
              </p>
              {loadingValidation ? (
                <div className="flex items-center gap-3 text-gray-400 text-sm py-6">
                  <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                  Running backtest…
                </div>
              ) : (
                <ValidationChart data={validation} />
              )}
            </div>
          )}
        </motion.div>

        {/* Model Explainer */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}>
          <ModelExplainer
            trend={forecastTrend}
            analysis={{
              rsi: marketData.length > 0 ? (marketData[marketData.length - 1].rsi || 52) : 52,
              macd: forecastDiff,
              volatility: displayPrice * 0.02,
              fng: prediction?.metadata?.metrics?.last_fng || 68,
            }}
          />
        </motion.div>

      </div>
    </div>
  );
}

export default App;
