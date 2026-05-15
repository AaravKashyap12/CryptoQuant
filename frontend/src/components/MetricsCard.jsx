import React, { useEffect, useMemo, useState } from 'react';
import { motion, useMotionValue, useMotionValueEvent, useSpring } from 'framer-motion';
import { Info } from 'lucide-react';

function parseDisplayValue(value) {
  const text = String(value ?? '');
  const match = text.match(/^([^0-9+-]*[+-]?)(\d[\d,]*(?:\.\d+)?)(.*)$/);
  if (!match) return null;

  const [, prefix, rawNumber, suffix] = match;
  const decimals = rawNumber.includes('.') ? rawNumber.split('.')[1].length : 0;
  const numeric = Number(rawNumber.replace(/,/g, ''));
  if (!Number.isFinite(numeric)) return null;

  return { prefix, numeric, suffix, decimals };
}

function AnimatedMetricValue({ value }) {
  const parsed = useMemo(() => parseDisplayValue(value), [value]);
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { stiffness: 260, damping: 28, mass: 0.45 });
  const [display, setDisplay] = useState(String(value ?? '-'));

  useEffect(() => {
    if (parsed) motionValue.set(parsed.numeric);
  }, [motionValue, parsed]);

  useMotionValueEvent(spring, 'change', latest => {
    if (!parsed) return;
    const formatted = latest.toLocaleString(undefined, {
      minimumFractionDigits: parsed.decimals,
      maximumFractionDigits: parsed.decimals,
    });
    setDisplay(`${parsed.prefix}${formatted}${parsed.suffix}`);
  });

  return <span>{parsed ? display : String(value ?? '-')}</span>;
}

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
      initial={{ opacity: 0, y: 28, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.52, delay: index * 0.12, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -5, scale: 1.012 }}
      className="t-card t-card-accent metric-card"
      style={{ padding: '24px 24px 22px', position: 'relative', overflow: 'visible', cursor: 'default', minHeight: '148px' }}
    >
      <div style={{
        position: 'absolute',
        top: 0,
        right: 0,
        width: '72px',
        height: '72px',
        background: `linear-gradient(225deg, ${accentColor}24 0%, transparent 68%)`,
        pointerEvents: 'none',
        borderRadius: '0 7px 0 0',
      }} />

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flexWrap: 'wrap' }}>
          {indicator === 'live' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div className="live-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--green)', flexShrink: 0 }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--green)', letterSpacing: '0.12em' }}>LIVE</span>
            </div>
          )}
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.13em', textTransform: 'uppercase' }}>
            {title}
          </span>
          {tooltip && (
            <span className="metric-tip-trigger" tabIndex={0} aria-label={tooltip}>
              <Info size={12} color="var(--text-muted)" style={{ cursor: 'help', display: 'block' }} />
              <span className="metric-tip-box">{tooltip}</span>
            </span>
          )}
        </div>

        {trend && (
          <div
            className="signal-badge"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 9px',
              background: isUp ? 'var(--green-dim)' : 'var(--red-dim)',
              border: `1px solid ${isUp ? 'rgba(0,230,118,0.26)' : 'rgba(255,23,68,0.26)'}`,
              borderRadius: '999px',
              color: isUp ? 'var(--green)' : 'var(--red)',
            }}
          >
            <span style={{ fontSize: '9px' }}>{isUp ? '\u25b2' : '\u25bc'}</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '0.1em' }}>
              {isUp ? 'BULLISH' : 'BEARISH'}
            </span>
          </div>
        )}
      </div>

      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 'clamp(28px, 3vw, 36px)',
        fontWeight: 700,
        color: 'var(--text-primary)',
        letterSpacing: 0,
        lineHeight: 1.03,
      }}>
        <AnimatedMetricValue value={value} />
      </div>

      {subValue && (
        <div style={{ marginTop: '10px', fontFamily: 'var(--font-mono)', fontSize: '12px', color: accentColor, letterSpacing: '0.04em' }}>
          {subValue}
        </div>
      )}

      <div style={{
        position: 'absolute',
        bottom: 0,
        left: '12%',
        right: '12%',
        height: '1px',
        background: `linear-gradient(90deg, transparent, ${accentColor}70, transparent)`,
      }} />
    </motion.div>
  );
}
