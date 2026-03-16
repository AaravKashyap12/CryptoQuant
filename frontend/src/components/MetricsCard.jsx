import React from 'react';
import { motion } from 'framer-motion';
import { Info } from 'lucide-react';

export function MetricsCard({ title, value, subValue, trend, tooltip, indicator, accent, index = 0 }) {
  const isUp = trend === 'up';
  const isDown = trend === 'down';

  const accentColor = accent
    ? accent
    : isUp ? 'var(--green)'
    : isDown ? 'var(--red)'
    : 'var(--accent)';

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.08 }}
      className="t-card t-card-accent"
      style={{ padding: '18px 20px', position: 'relative', overflow: 'hidden', cursor: 'default' }}
    >
      {/* Corner accent */}
      <div style={{ position: 'absolute', top: 0, right: 0, width: '40px', height: '40px', background: `linear-gradient(225deg, ${accentColor}18 0%, transparent 70%)`, pointerEvents: 'none' }} />

      {/* Label row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {indicator === 'live' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div className="live-dot" style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--green)', flexShrink: 0 }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--green)', letterSpacing: '0.12em' }}>LIVE</span>
            </div>
          )}
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
            {title}
          </span>
          {tooltip && (
            <div style={{ position: 'relative', display: 'inline-block' }} className="group/tip">
              <Info size={11} color="var(--text-muted)" style={{ cursor: 'help' }} />
              <div style={{ position: 'absolute', bottom: '140%', left: '50%', transform: 'translateX(-50%)', width: '180px', padding: '8px 10px', background: '#0a1520', border: '1px solid var(--border-bright)', borderRadius: '3px', fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.5, whiteSpace: 'normal', pointerEvents: 'none', opacity: 0, transition: 'opacity 0.15s', zIndex: 50 }}
                className="tip-box">
                {tooltip}
              </div>
            </div>
          )}
        </div>

        {/* Trend badge */}
        {trend && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '3px 8px', background: isUp ? 'var(--green-dim)' : 'var(--red-dim)', border: `1px solid ${isUp ? 'rgba(0,230,118,0.2)' : 'rgba(255,23,68,0.2)'}`, borderRadius: '2px' }}>
            <span style={{ fontSize: '9px', color: isUp ? 'var(--green)' : 'var(--red)' }}>{isUp ? '▲' : '▼'}</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: isUp ? 'var(--green)' : 'var(--red)', letterSpacing: '0.1em' }}>
              {isUp ? 'BULLISH' : 'BEARISH'}
            </span>
          </div>
        )}
      </div>

      {/* Value */}
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '26px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
        {value}
      </div>

      {/* Sub value */}
      {subValue && (
        <div style={{ marginTop: '6px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: accentColor, letterSpacing: '0.04em' }}>
          {subValue}
        </div>
      )}

      {/* Bottom line accent */}
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: '1px', background: `linear-gradient(90deg, transparent, ${accentColor}40, transparent)` }} />
    </motion.div>
  );
}