import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Cpu } from 'lucide-react';

function GaugeBar({ value, max = 100, color }) {
  const pct = Math.min(Math.max(value / max, 0), 1) * 100;
  return (
    <div style={{ height: '3px', background: 'var(--border)', borderRadius: '2px', position: 'relative', marginTop: '8px' }}>
      <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${pct}%`, background: color, borderRadius: '2px', boxShadow: `0 0 6px ${color}80`, transition: 'width 0.8s ease' }} />
    </div>
  );
}

function StatBlock({ label, value, valueColor, sub, gauge, gaugeColor }) {
  return (
    <div style={{ padding: '14px 16px', background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: '3px' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.15em', marginBottom: '8px' }}>
        {label}
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 600, color: valueColor || 'var(--text-primary)' }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px', letterSpacing: '0.06em' }}>
          {sub}
        </div>
      )}
      {gauge != null && <GaugeBar value={gauge} color={gaugeColor || 'var(--accent)'} />}
    </div>
  );
}

export function ModelExplainer({ trend, analysis }) {
  const [open, setOpen] = useState(true);

  const rsi = analysis?.rsi || 50;
  const macd = analysis?.macd || 0;
  const vol = analysis?.volatility || 0;
  const fng = analysis?.fng || 50;

  const isUp = trend === 'up';

  const fngColor = fng >= 60 ? 'var(--green)' : fng <= 40 ? 'var(--red)' : 'var(--yellow)';
  const fngLabel = fng >= 75 ? 'EXTREME GREED' : fng >= 55 ? 'GREED' : fng <= 25 ? 'EXTREME FEAR' : fng <= 45 ? 'FEAR' : 'NEUTRAL';
  const rsiColor = rsi > 70 ? 'var(--red)' : rsi < 30 ? 'var(--green)' : 'var(--text-primary)';
  const rsiLabel = rsi > 70 ? 'OVERBOUGHT' : rsi < 30 ? 'OVERSOLD' : 'NEUTRAL';

  return (
    <div className="t-card" style={{ overflow: 'hidden' }}>
      {/* Header */}
      <button
        onClick={() => setOpen(!open)}
        style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', background: 'transparent', border: 'none', cursor: 'pointer', borderBottom: open ? '1px solid var(--border)' : 'none' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Cpu size={14} color="var(--accent)" />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)', letterSpacing: '0.12em' }}>
            MODEL ANALYSIS &amp; SIGNAL BREAKDOWN
          </span>
          <div style={{ padding: '2px 8px', background: isUp ? 'var(--green-dim)' : 'var(--red-dim)', border: `1px solid ${isUp ? 'rgba(0,230,118,0.25)' : 'rgba(255,23,68,0.25)'}`, borderRadius: '2px' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600, color: isUp ? 'var(--green)' : 'var(--red)', letterSpacing: '0.12em' }}>
              {isUp ? '▲ BULLISH' : '▼ BEARISH'}
            </span>
          </div>
        </div>
        {open
          ? <ChevronUp size={14} color="var(--text-muted)" />
          : <ChevronDown size={14} color="var(--text-muted)" />
        }
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ padding: '16px 20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '10px' }}>

              <StatBlock
                label="AI BIAS"
                value={isUp ? 'BULLISH' : 'BEARISH'}
                valueColor={isUp ? 'var(--green)' : 'var(--red)'}
                sub="Hybrid LSTM-CNN signal"
              />

              <StatBlock
                label="FEAR & GREED INDEX"
                value={fng.toString()}
                valueColor={fngColor}
                sub={fngLabel}
                gauge={fng}
                gaugeColor={fngColor}
              />

              <StatBlock
                label="RSI MOMENTUM"
                value={rsi.toFixed(1)}
                valueColor={rsiColor}
                sub={rsiLabel}
                gauge={rsi}
                gaugeColor={rsiColor}
              />

              <StatBlock
                label="MACD TREND"
                value={macd > 0 ? 'POSITIVE' : 'NEGATIVE'}
                valueColor={macd > 0 ? 'var(--green)' : 'var(--red)'}
                sub={macd > 0 ? 'Buying pressure dominant' : 'Selling pressure dominant'}
              />

              <StatBlock
                label="VOLATILITY RISK"
                value={`±${Number(vol).toFixed(1)}%`}
                valueColor="var(--accent)"
                sub="Est. daily price range"
              />

            </div>

            {/* Info bar */}
            <div style={{ margin: '0 20px 16px', padding: '10px 14px', background: 'rgba(0,212,255,0.04)', border: '1px solid rgba(0,212,255,0.12)', borderRadius: '3px', display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
              <span style={{ color: 'var(--accent)', fontSize: '12px', marginTop: '1px', flexShrink: 0 }}>ℹ</span>
              <p style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-secondary)', lineHeight: 1.7, letterSpacing: '0.02em' }}>
                Predictions generated by a <strong style={{ color: 'var(--accent)' }}>Hybrid LSTM-CNN Ensemble</strong> with Monte Carlo Dropout (n=20). 
                Trained on 1500+ daily candles per coin using 15 engineered features including Wilder RSI, MACD, EMA, ATR, and the Fear &amp; Greed Index.
                Confidence bands represent the 5th–95th percentile range across stochastic inference passes.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}