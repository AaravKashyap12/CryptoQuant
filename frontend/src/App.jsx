import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CoinSelector } from './components/CoinSelector';
import { MetricsCard } from './components/MetricsCard';
import { PriceChart } from './components/PriceChart';
import { ModelExplainer } from './components/ModelExplainer';
import { ValidationChart } from './components/ValidationChart';
import { OnChainPanel } from './components/OnChainPanel';
import { RefreshCw, BarChart2, Terminal, AlertCircle, Activity } from 'lucide-react';
import { getCoins, getMarketData, getPrediction, getValidation, getSentiment, getOnChainSignals } from './lib/api';
import { useLivePrice } from './hooks/useLivePrice';

function ConfidenceSignal({ spread }) {
  if (spread == null) return null;

  const isHigh = spread < 3;
  const isMedium = spread >= 3 && spread < 7;
  const label = isHigh ? 'HIGH CONFIDENCE' : isMedium ? 'MODERATE' : 'NO SIGNAL';
  const color = isHigh ? 'var(--green)' : isMedium ? 'var(--yellow)' : 'var(--red)';
  const dim = isHigh ? 'var(--green-dim)' : isMedium ? 'var(--yellow-dim)' : 'var(--red-dim)';
  const border = isHigh ? 'rgba(0,230,118,0.25)' : isMedium ? 'rgba(255,214,0,0.25)' : 'rgba(255,23,68,0.25)';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 10px', background: dim, border: `1px solid ${border}`, borderRadius: '2px' }}>
      <div style={{ width: '5px', height: '5px', borderRadius: '50%', background: color, boxShadow: `0 0 6px ${color}` }} />
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color, letterSpacing: '0.12em' }}>
        {label}
      </span>
    </div>
  );
}

function ForecastCard({ forecast, currentPrice }) {
  if (!forecast?.mean?.length) return null;

  const price = forecast.mean[0];
  const upper = forecast.upper?.[0];
  const lower = forecast.lower?.[0];
  const change = currentPrice ? ((price - currentPrice) / currentPrice) * 100 : 0;
  const spread = price && upper != null && lower != null ? ((upper - lower) / price) * 100 : 0;
  const isUp = change >= 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4 }}
      className="forecast-summary-card"
      style={{
        padding: '16px 20px',
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderTop: `2px solid ${isUp ? 'var(--green)' : 'var(--red)'}`,
        borderRadius: '3px',
        marginBottom: '10px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '16px',
        alignItems: 'center',
      }}
    >
      <div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.15em', marginBottom: '6px' }}>
          NEXT-DAY FORECAST
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: 700, color: 'var(--yellow)', letterSpacing: '-0.02em' }}>
          ${price >= 10000
            ? `${(price / 1000).toFixed(2)}k`
            : price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: isUp ? 'var(--green)' : 'var(--red)', marginTop: '4px' }}>
          {isUp ? 'UP +' : 'DOWN '}{Math.abs(change).toFixed(2)}% from today
        </div>
      </div>

      <div className="forecast-summary-section">
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: '10px' }}>
          90% CONFIDENCE BAND
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
            <span style={{ color: 'var(--text-muted)' }}>HIGH</span>
            <span style={{ color: 'var(--green)' }}>${upper?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
          </div>
          <div style={{ height: '4px', background: 'var(--border)', borderRadius: '2px', position: 'relative' }}>
            <div style={{ position: 'absolute', left: '20%', right: '20%', top: 0, height: '100%', background: 'linear-gradient(90deg, var(--red), var(--yellow), var(--green))', borderRadius: '2px', opacity: 0.6 }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
            <span style={{ color: 'var(--text-muted)' }}>LOW</span>
            <span style={{ color: 'var(--red)' }}>${lower?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
          </div>
        </div>
      </div>

      <div className="forecast-summary-section">
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: '6px' }}>
          UNCERTAINTY SPREAD
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '22px', fontWeight: 600, color: 'var(--accent)' }}>
          &#177;{(spread / 2).toFixed(2)}%
        </div>
        <div style={{ marginTop: '6px' }}>
          <ConfidenceSignal spread={spread} />
        </div>
      </div>
    </motion.div>
  );
}

function StatusBar({ prediction, selectedCoin, onRefresh, refreshing }) {
  const [time, setTime] = useState(() => `${new Date().toUTCString().split(' ')[4]} UTC`);

  useEffect(() => {
    const timer = setInterval(() => setTime(`${new Date().toUTCString().split(' ')[4]} UTC`), 1000);
    return () => clearInterval(timer);
  }, []);

  const mcIterations = prediction?.metadata?.mc_iterations ?? 50;
  const servingMode = prediction?.metadata?.serving_mode || 'weighted ensemble';
  const isEligible = prediction?.metadata?.eligible_for_cached_serving !== false;

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '7px 0 12px', flexWrap: 'wrap', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div className="live-dot" style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--green)' }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>SYSTEM ONLINE</span>
        </div>

        {prediction?.from_cache && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--accent)', letterSpacing: '0.08em' }}>CACHE HIT</span>
            {prediction.computed_at && (
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
                - {new Date(prediction.computed_at).toLocaleString()}
              </span>
            )}
          </div>
        )}

        {!isEligible && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '2px 8px', background: 'var(--red-dim)', border: '1px solid rgba(255,23,68,0.2)', borderRadius: '2px' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--red)', letterSpacing: '0.08em' }}>MODEL UNDER REVIEW</span>
          </div>
        )}

        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>
          {selectedCoin}/USDT - {servingMode.toUpperCase()} - MC={mcIterations}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>{time}</span>
        <button onClick={onRefresh} disabled={refreshing} className="t-btn" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <RefreshCw size={10} style={{ animation: refreshing ? 'spin 0.8s linear infinite' : 'none' }} />
          REFRESH
        </button>
      </div>
    </div>
  );
}

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
  const [sentimentData, setSentimentData] = useState(null);
  const [onChainData, setOnChainData] = useState(null);
  const [error, setError] = useState(null);

  const { price: livePrice, change24h: liveChange } = useLivePrice(`${selectedCoin}USDT`);

  const loadCoreData = useCallback(async (coin) => {
    setLoading(true);
    setMarketData([]);
    setPrediction(null);
    setValidation(null);
    setOnChainData(null);
    setShowValidation(false);
    try {
      const [mData, predData, onChain] = await Promise.all([
        getMarketData(coin),
        getPrediction(coin).catch(() => null),
        getOnChainSignals(coin).catch(() => null),
      ]);
      setMarketData(mData || []);
      setPrediction(predData);
      setOnChainData(onChain);
    } catch (e) {
      console.error('Load error', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let retries = 5;
    async function init() {
      try {
        const [coinList, sentiment] = await Promise.all([
          getCoins(),
          getSentiment().catch(() => null),
        ]);
        setCoins(coinList || []);
        setSentimentData(sentiment);
        setError(null);
      } catch {
        if (retries-- > 0) setTimeout(init, 3000);
        else setError('Backend unreachable. Check your deployment.');
      }
    }
    init();
  }, []);

  useEffect(() => {
    if (selectedCoin && coins.length > 0) loadCoreData(selectedCoin);
  }, [selectedCoin, coins, loadCoreData]);

  const handleShowValidation = useCallback(async () => {
    if (validation) {
      setShowValidation(true);
      return;
    }
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
    const [sentiment] = await Promise.all([
      getSentiment().catch(() => null),
      loadCoreData(selectedCoin),
    ]);
    if (sentiment) setSentimentData(sentiment);
    setRefreshing(false);
  };

  const handleCoinSelect = (coin) => {
    setSelectedCoin(coin);
    setValidation(null);
    setShowValidation(false);
  };

  const currentPrice = marketData.length > 0 ? marketData[marketData.length - 1]?.close ?? 0 : 0;
  const prevPrice = marketData.length > 1 ? marketData[marketData.length - 2]?.close ?? currentPrice : currentPrice;
  const percentChange = prevPrice !== 0 ? ((currentPrice - prevPrice) / prevPrice) * 100 : 0;
  const displayPrice = livePrice ?? currentPrice;
  const displayChange = liveChange ?? percentChange;
  const basePrice = displayPrice || currentPrice;

  const nextDayPred = prediction?.forecast?.mean?.[0] ?? 0;
  const forecastTrend = nextDayPred >= basePrice ? 'up' : 'down';
  const forecastDiff = basePrice !== 0 ? ((nextDayPred - basePrice) / basePrice) * 100 : 0;
  const upper = prediction?.forecast?.upper?.[0] ?? 0;
  const lower = prediction?.forecast?.lower?.[0] ?? 0;
  const spread = nextDayPred !== 0 ? ((upper - lower) / nextDayPred) * 100 : 0;

  const realVolatility = useMemo(() => {
    if (marketData.length < 5) return 0;
    const recent = marketData.slice(-21);
    const returns = recent.slice(1)
      .map((d, i) => {
        const previous = recent[i]?.close;
        return previous ? Math.abs((d.close - previous) / previous) * 100 : 0;
      })
      .filter(Boolean);
    if (!returns.length) return 0;
    return returns.reduce((a, b) => a + b, 0) / returns.length;
  }, [marketData]);

  const realRSI = marketData.length > 0 ? (marketData[marketData.length - 1]?.rsi ?? 50) : 50;
  const realFNG = sentimentData?.sentiment_score ?? prediction?.metadata?.metrics?.last_fng ?? 50;

  return (
    <div className="grid-bg" style={{ minHeight: '100vh', position: 'relative' }}>
      <div className="scanlines" style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none' }} />

      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{ position: 'fixed', inset: 0, zIndex: 100, background: 'rgba(8,11,15,0.9)', backdropFilter: 'blur(4px)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px' }}
          >
            <div style={{ width: '40px', height: '40px', border: '1px solid var(--border-bright)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--accent)', letterSpacing: '0.15em' }} className="blink-cursor">
              LOADING {selectedCoin} MARKET DATA
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <CoinSelector coins={coins} selectedCoin={selectedCoin} onSelect={handleCoinSelect} livePrice={displayPrice} change24h={displayChange} />

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            style={{ background: 'rgba(255,23,68,0.07)', borderBottom: '1px solid rgba(255,23,68,0.18)', padding: '8px 24px', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <AlertCircle size={12} color="var(--red)" />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--red)', letterSpacing: '0.06em' }}>{error}</span>
          </motion.div>
        )}
      </AnimatePresence>

      <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '16px 24px 48px' }}>
        <StatusBar prediction={prediction} selectedCoin={selectedCoin} onRefresh={handleRefresh} refreshing={refreshing} />

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '10px' }}>
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
            title="1-Day Ensemble Forecast"
            value={prediction ? `$${nextDayPred.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '-'}
            subValue={prediction ? `${forecastDiff >= 0 ? '+' : ''}${forecastDiff.toFixed(2)}% from now` : 'Awaiting model...'}
            trend={forecastTrend}
            accent="var(--yellow)"
            tooltip="Weighted ensemble combines neural, tree, and persistence signals."
          />
          <MetricsCard
            index={2}
            title="Model Uncertainty"
            value={prediction ? `\u00b1${(spread / 2).toFixed(2)}%` : '-'}
            subValue={prediction ? `$${lower.toLocaleString(undefined, { maximumFractionDigits: 0 })} - $${upper.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '90% confidence interval'}
            accent="var(--accent)"
            tooltip={`Spread: ${spread.toFixed(2)}% - wider bands indicate higher model uncertainty.`}
          />
        </div>

        {prediction?.forecast && <ForecastCard forecast={prediction.forecast} currentPrice={basePrice} />}

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.4 }}
          className="t-card t-card-accent"
          style={{ padding: '20px', marginBottom: '10px' }}
        >
          <PriceChart data={marketData} forecast={prediction?.forecast} />
        </motion.div>

        <div className="analysis-grid" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 360px', gap: '10px', marginBottom: '10px', alignItems: 'start' }}>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.45 }}>
            <ModelExplainer
              trend={forecastTrend}
              analysis={{
                rsi: realRSI,
                macd: forecastDiff,
                volatility: realVolatility,
                fng: realFNG,
              }}
              modelMeta={prediction?.metadata}
            />
          </motion.div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
            <OnChainPanel coin={selectedCoin} data={onChainData} loading={loading} />
          </motion.div>
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.55 }}>
          {!showValidation ? (
            <button onClick={handleShowValidation} className="t-btn" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '9px 18px' }}>
              <BarChart2 size={11} />
              RUN 30-DAY WALK-FORWARD BACKTEST
            </button>
          ) : (
            <div className="t-card t-card-accent" style={{ padding: '16px 20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
                <Activity size={13} color="var(--accent)" />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)', letterSpacing: '0.1em' }}>
                  MODEL ACCURACY - LAST 30 DAYS
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', marginLeft: 'auto' }}>ROLLING BACKTEST</span>
              </div>
              {loadingValidation ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '24px 0', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
                  <div style={{ width: '18px', height: '18px', border: '1px solid var(--border-bright)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                  RUNNING BACKTEST...
                </div>
              ) : (
                <ValidationChart data={validation} />
              )}
            </div>
          )}
        </motion.div>

        <div style={{ marginTop: '40px', paddingTop: '16px', borderTop: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={11} color="var(--text-muted)" />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                CRYPTOQUANT v2.1 - FOR EDUCATIONAL USE ONLY - NOT FINANCIAL ADVICE
              </span>
            </div>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              BUILT BY AARAV KASHYAP
            </span>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @media (max-width: 900px) {
          .analysis-grid {
            grid-template-columns: 1fr !important;
          }
        }
        @media (max-width: 640px) {
          div[style*="grid-template-columns: repeat(3"] {
            grid-template-columns: 1fr !important;
          }
          .forecast-summary-section {
            border-left: 0 !important;
            padding-left: 0 !important;
            border-top: 1px solid var(--border);
            padding-top: 12px;
          }
        }
      `}</style>
    </div>
  );
}

export default App;
