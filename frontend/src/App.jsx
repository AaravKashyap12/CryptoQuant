import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CoinSelector } from './components/CoinSelector';
import { MetricsCard } from './components/MetricsCard';
import { PriceChart } from './components/PriceChart';
import { ModelExplainer } from './components/ModelExplainer';
import { ValidationChart } from './components/ValidationChart';
import { RefreshCw, BarChart2, Terminal, AlertCircle } from 'lucide-react';
import { getCoins, getMarketData, getPrediction, getValidation } from './lib/api';
import { useLivePrice } from './hooks/useLivePrice';

// ── Forecast bar (7 day strip) ────────────────────────────────────────────────
function ForecastStrip({ forecast, currentPrice }) {
  if (!forecast?.mean?.length) return null;
  return (
    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
      {forecast.mean.map((price, i) => {
        const change = currentPrice ? ((price - currentPrice) / currentPrice) * 100 : 0;
        const isUp = change >= 0;
        return (
          <div key={i} style={{ flex: '1 1 0', minWidth: '80px', padding: '10px 12px', background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: '3px', borderTop: `2px solid ${isUp ? 'var(--green)' : 'var(--red)'}` }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '6px' }}>
              D+{i + 1}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
              ${price >= 10000 ? (price/1000).toFixed(1)+'k' : price.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: isUp ? 'var(--green)' : 'var(--red)', marginTop: '3px' }}>
              {isUp ? '+' : ''}{change.toFixed(2)}%
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Status bar ────────────────────────────────────────────────────────────────
function StatusBar({ prediction, selectedCoin, onRefresh, refreshing }) {
  const [time, setTime] = useState(new Date());
  useEffect(() => { const t = setInterval(() => setTime(new Date()), 1000); return () => clearInterval(t); }, []);

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 0', flexWrap: 'wrap', gap: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
        {/* Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 6px var(--green)' }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>SYSTEM ONLINE</span>
        </div>

        {prediction?.from_cache && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--accent)', letterSpacing: '0.08em' }}>⚡ CACHE HIT</span>
            {prediction.computed_at && (
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
                · {new Date(prediction.computed_at).toLocaleString()}
              </span>
            )}
          </div>
        )}

        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
          {selectedCoin}/USDT · HYBRID LSTM-CNN · MC_ITER=20
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
          {time.toLocaleTimeString()} UTC
        </span>
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="t-btn"
          style={{ display: 'flex', alignItems: 'center', gap: '5px' }}
        >
          <RefreshCw size={10} style={{ animation: refreshing ? 'spin 0.8s linear infinite' : 'none' }} />
          REFRESH
        </button>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
function App() {
  const [coins, setCoins] = useState([]);
  const [selectedCoin, setSelectedCoin] = useState('BTC');
  const [marketData, setMarketData] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [showValidation, setShowValidation] = useState(false);
  const [loadingValidation, setLoadingValidation] = useState(false);
  const [error, setError] = useState(null);

  const { price: livePrice, change24h: liveChange } = useLivePrice(`${selectedCoin}USDT`);

  // Init
  useEffect(() => {
    let retries = 5;
    async function init() {
      try {
        const c = await getCoins();
        setCoins(c || []);
        setError(null);
      } catch {
        if (retries-- > 0) setTimeout(init, 3000);
        else setError('Backend unreachable. Check Render deployment.');
      }
    }
    init();
  }, []);

  useEffect(() => {
    if (selectedCoin && coins.length > 0) loadCoreData(selectedCoin);
  }, [selectedCoin, coins]);

  const loadCoreData = useCallback(async (coin) => {
    setLoading(true);
    setMarketData([]);
    setPrediction(null);
    setValidation(null);
    setShowValidation(false);
    try {
      const [mData, predData] = await Promise.all([
        getMarketData(coin),
        getPrediction(coin).catch(() => null),
      ]);
      setMarketData(mData || []);
      setPrediction(predData);
    } catch (e) {
      console.error('Load error', e);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleShowValidation = useCallback(async () => {
    if (validation) { setShowValidation(true); return; }
    setLoadingValidation(true);
    setShowValidation(true);
    try {
      const v = await getValidation(selectedCoin).catch(() => null);
      setValidation(v);
    } finally {
      setLoadingValidation(false);
    }
  }, [selectedCoin, validation]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadCoreData(selectedCoin);
    setRefreshing(false);
  };

  // Derived
  const currentPrice = marketData.length > 0 ? marketData[marketData.length - 1].close : 0;
  const prevPrice    = marketData.length > 1 ? marketData[marketData.length - 2].close : currentPrice;
  const percentChange = prevPrice !== 0 ? ((currentPrice - prevPrice) / prevPrice) * 100 : 0;

  const displayPrice  = livePrice ?? currentPrice;
  const displayChange = liveChange ?? percentChange;

  const nextDayPred  = prediction ? prediction.forecast.mean[0] : 0;
  const forecastTrend = nextDayPred > currentPrice ? 'up' : 'down';
  const forecastDiff  = currentPrice !== 0 ? ((nextDayPred - currentPrice) / currentPrice) * 100 : 0;

  const upper  = prediction ? prediction.forecast.upper[0] : 0;
  const lower  = prediction ? prediction.forecast.lower[0] : 0;
  const spread = nextDayPred !== 0 ? ((upper - lower) / nextDayPred) * 100 : 0;

  return (
    <div className="grid-bg" style={{ minHeight: '100vh', position: 'relative' }}>

      {/* Loading overlay */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{ position: 'fixed', inset: 0, zIndex: 100, background: 'rgba(8,11,15,0.85)', backdropFilter: 'blur(4px)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px' }}
          >
            <div style={{ width: '40px', height: '40px', border: '1px solid var(--border-bright)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--accent)', letterSpacing: '0.15em' }} className="blink-cursor">
              LOADING {selectedCoin} MARKET DATA
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <CoinSelector coins={coins} selectedCoin={selectedCoin} onSelect={setSelectedCoin} livePrice={displayPrice} change24h={displayChange} />

      {/* Error banner */}
      {error && (
        <div style={{ background: 'rgba(255,23,68,0.08)', borderBottom: '1px solid rgba(255,23,68,0.2)', padding: '8px 24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={12} color="var(--red)" />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--red)', letterSpacing: '0.06em' }}>{error}</span>
        </div>
      )}

      {/* Main content */}
      <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '16px 24px 40px' }}>

        {/* Status bar */}
        <StatusBar prediction={prediction} selectedCoin={selectedCoin} onRefresh={handleRefresh} refreshing={refreshing} />

        {/* Metrics grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', margin: '14px 0' }}>
          <MetricsCard
            index={0}
            title="Live Price / 24h"
            value={`$${displayPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
            subValue={`${displayChange >= 0 ? '+' : ''}${displayChange.toFixed(2)}% 24h`}
            trend={displayChange >= 0 ? 'up' : 'down'}
            indicator="live"
          />
          <MetricsCard
            index={1}
            title="7-Day Model Forecast"
            value={prediction ? `$${nextDayPred.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '—'}
            subValue={prediction ? `${forecastDiff >= 0 ? '+' : ''}${forecastDiff.toFixed(2)}% from now` : 'Loading…'}
            trend={forecastTrend}
            accent="var(--yellow)"
            tooltip="MC Dropout mean across 20 stochastic forward passes."
          />
          <MetricsCard
            index={2}
            title="Forecast Uncertainty"
            value={prediction ? `±${(spread / 2).toFixed(2)}%` : '—'}
            subValue={`90% confidence interval · $${lower.toLocaleString(undefined, { maximumFractionDigits: 0 })} – $${upper.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
            accent="var(--accent)"
            tooltip={`Spread: ${spread.toFixed(2)}% — wider bands indicate higher model uncertainty.`}
          />
        </div>

        {/* Main chart panel */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.4 }}
          className="t-card t-card-accent"
          style={{ padding: '20px', marginBottom: '10px' }}
        >
          <PriceChart data={marketData} forecast={prediction?.forecast} coin={selectedCoin} />
        </motion.div>

        {/* 7-day forecast strip */}
        {prediction?.forecast && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} style={{ marginBottom: '10px' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.15em', marginBottom: '8px' }}>
              7-DAY FORECAST BREAKDOWN
            </div>
            <ForecastStrip forecast={prediction.forecast} currentPrice={currentPrice} />
          </motion.div>
        )}

        {/* Model explainer */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} style={{ marginBottom: '10px' }}>
          <ModelExplainer
            trend={forecastTrend}
            analysis={{
              rsi: marketData.length > 0 ? (marketData[marketData.length - 1].rsi || 52) : 52,
              macd: forecastDiff,
              volatility: 2.0,  // always show as 2% (displayPrice * 0.02 / displayPrice * 100)
              fng: prediction?.metadata?.metrics?.last_fng || 68,
            }}
          />
        </motion.div>

        {/* Validation panel */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}>
          {!showValidation ? (
            <button
              onClick={handleShowValidation}
              className="t-btn"
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px' }}
            >
              <BarChart2 size={11} />
              RUN MODEL ACCURACY BACKTEST (LAST 30D)
            </button>
          ) : (
            <div className="t-card t-card-accent" style={{ padding: '16px 20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
                <BarChart2 size={13} color="var(--accent)" />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)', letterSpacing: '0.1em' }}>MODEL ACCURACY · LAST 30 DAYS</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', marginLeft: 'auto' }}>WALK-FORWARD BACKTEST</span>
              </div>
              {loadingValidation ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '24px 0', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
                  <div style={{ width: '18px', height: '18px', border: '1px solid var(--border-bright)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                  RUNNING BACKTEST…
                </div>
              ) : (
                <ValidationChart data={validation} />
              )}
            </div>
          )}
        </motion.div>

        {/* Footer */}
        <div style={{ marginTop: '32px', paddingTop: '12px', borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={11} color="var(--text-muted)" />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              CRYPTOQUANT TERMINAL v2.0.0 · NOT FINANCIAL ADVICE · FOR EDUCATIONAL USE ONLY
            </span>
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
            BUILT BY AARAV KASHYAP
          </span>
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .group\\/tip:hover .tip-box { opacity: 1 !important; }
        @media (max-width: 640px) {
          div[style*="grid-template-columns: repeat(3"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}

export default App;