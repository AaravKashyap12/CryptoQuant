import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Cpu } from 'lucide-react';

function GaugeBar({ value, max = 100, color }) {
  const pct = Math.min(Math.max(value / max, 0), 1) * 100;
  return (
    <div style={{ height: '3px', background: 'var(--border)', borderRadius: '2px', position: 'relative', marginTop: '8px' }}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          height: '100%',
          width: `${pct}%`,
          background: color,
          borderRadius: '2px',
          boxShadow: `0 0 6px ${color}80`,
          transition: 'width 0.8s ease',
        }}
      />
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

function EnsembleWeights({ servingMode }) {
  const isWeighted = String(servingMode || '').toLowerCase().includes('weighted');
  const weights = isWeighted
    ? [
        { label: 'NEURAL', pct: 50, color: 'var(--accent)' },
        { label: 'TREE', pct: 30, color: 'var(--yellow)' },
        { label: 'PERSISTENCE', pct: 20, color: 'var(--text-muted)' },
      ]
    : [
        { label: 'TREE', pct: 50, color: 'var(--yellow)' },
        { label: 'PERSISTENCE', pct: 50, color: 'var(--text-muted)' },
      ];

  return (
    <div style={{ padding: '12px 16px', background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: '3px' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.15em', marginBottom: '12px' }}>
        ENSEMBLE COMPOSITION
      </div>
      <div style={{ display: 'flex', height: '6px', borderRadius: '3px', overflow: 'hidden', marginBottom: '10px' }}>
        {weights.map((w) => (
          <div key={w.label} style={{ width: `${w.pct}%`, background: w.color, transition: 'width 0.6s ease' }} />
        ))}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
        {weights.map((w) => (
          <div key={w.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '6px', height: '6px', borderRadius: '1px', background: w.color, flexShrink: 0 }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>
                {w.label}
              </span>
            </div>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600, color: w.color }}>{w.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ModelExplainer({ trend, analysis, modelMeta }) {
  const [open, setOpen] = useState(true);

  const rsi = analysis?.rsi ?? 50;
  const macd = analysis?.macd ?? 0;
  const vol = analysis?.volatility ?? 0;
  const fng = analysis?.fng ?? 50;
  const isUp = trend === 'up';

  const fngColor = fng >= 60 ? 'var(--green)' : fng <= 40 ? 'var(--red)' : 'var(--yellow)';
  const fngLabel = fng >= 75 ? 'EXTREME GREED' : fng >= 55 ? 'GREED' : fng <= 25 ? 'EXTREME FEAR' : fng <= 45 ? 'FEAR' : 'NEUTRAL';
  const rsiColor = rsi > 70 ? 'var(--red)' : rsi < 30 ? 'var(--green)' : 'var(--text-primary)';
  const rsiLabel = rsi > 70 ? 'OVERBOUGHT' : rsi < 30 ? 'OVERSOLD' : 'NEUTRAL';
  const volColor = vol > 5 ? 'var(--red)' : vol > 2 ? 'var(--yellow)' : 'var(--green)';

  const modelVersion = modelMeta?.version || '-';
  const dirAccuracy = modelMeta?.metrics?.directional_accuracy;
  const trainSamples = modelMeta?.metrics?.train_samples;
  const servingMode = modelMeta?.serving_mode || 'weighted ensemble';
  const mcIterations = modelMeta?.mc_iterations ?? 50;

  return (
    <div className="t-card" style={{ overflow: 'hidden' }}>
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
              {isUp ? 'BULLISH' : 'BEARISH'}
            </span>
          </div>
        </div>
        {open ? <ChevronUp size={14} color="var(--text-muted)" /> : <ChevronDown size={14} color="var(--text-muted)" />}
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
            <div style={{ padding: '16px 20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px' }}>
              <StatBlock label="AI BIAS" value={isUp ? 'BULLISH' : 'BEARISH'} valueColor={isUp ? 'var(--green)' : 'var(--red)'} sub="Ensemble forecast direction" />
              <StatBlock label="FEAR & GREED" value={Math.round(fng).toString()} valueColor={fngColor} sub={fngLabel} gauge={fng} gaugeColor={fngColor} />
              <StatBlock label="RSI MOMENTUM" value={rsi.toFixed(1)} valueColor={rsiColor} sub={rsiLabel} gauge={rsi} gaugeColor={rsiColor} />
              <StatBlock label="MACD TREND" value={macd > 0 ? 'POSITIVE' : 'NEGATIVE'} valueColor={macd > 0 ? 'var(--green)' : 'var(--red)'} sub={macd > 0 ? 'Buying pressure' : 'Selling pressure'} />
              <StatBlock label="DAILY VOLATILITY" value={`${vol.toFixed(2)}%`} valueColor={volColor} sub={vol > 5 ? 'HIGH RISK' : vol > 2 ? 'MODERATE' : 'LOW RISK'} gauge={Math.min(vol * 10, 100)} gaugeColor={volColor} />
              <EnsembleWeights servingMode={servingMode} />
            </div>

            {(modelVersion !== '-' || dirAccuracy != null || trainSamples != null) && (
              <div style={{ margin: '0 20px 4px', padding: '8px 14px', background: 'rgba(0,212,255,0.03)', border: '1px solid rgba(0,212,255,0.1)', borderRadius: '3px', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                {modelVersion !== '-' && (
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>
                    MODEL <span style={{ color: 'var(--accent)' }}>{modelVersion}</span>
                  </div>
                )}
                {dirAccuracy != null && (
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>
                    DIR. ACCURACY{' '}
                    <span style={{ color: dirAccuracy >= 0.55 ? 'var(--green)' : 'var(--yellow)' }}>
                      {(dirAccuracy * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
                {trainSamples != null && (
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>
                    TRAINED ON <span style={{ color: 'var(--text-secondary)' }}>{trainSamples} SAMPLES</span>
                  </div>
                )}
              </div>
            )}

            <div style={{ margin: '8px 20px 16px', padding: '10px 14px', background: 'rgba(0,212,255,0.04)', border: '1px solid rgba(0,212,255,0.12)', borderRadius: '3px', display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
              <span style={{ color: 'var(--accent)', fontSize: '12px', marginTop: '1px', flexShrink: 0 }}>i</span>
              <p style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-secondary)', lineHeight: 1.7, letterSpacing: '0.02em' }}>
                Forecasts are served by a <strong style={{ color: 'var(--accent)' }}>{servingMode}</strong> path.
                Neural uncertainty uses <strong style={{ color: 'var(--accent)' }}>{mcIterations} Monte Carlo passes</strong> when the model output is eligible.
                The persistence anchor keeps the forecast close to the latest market price when signal quality is weak.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
