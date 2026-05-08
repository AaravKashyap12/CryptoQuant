import React from 'react';
import { motion } from 'framer-motion';
import { Info } from 'lucide-react';

export function MetricsCard({ title, value, subValue, trend, tooltip, indicator, accent, index = 0 }) {
  const isUp   = trend === 'up';
  const isDown = trend === 'down';

  const accentColor = accent
    ? accent
    : isUp   ? 'var(--green)'
    : isDown ? 'var(--red)'
    : 'var(--accent)';

  return (
    <motion.div
      initial={{ opacity:0, y:16 }}
      animate={{ opacity:1, y:0 }}
      transition={{ duration:0.3, delay: index * 0.08 }}
      className="t-card t-card-accent metric-card"
      style={{ padding:'18px 20px', position:'relative', overflow:'visible', cursor:'default' }}
    >
      {/* Corner accent */}
      <div style={{ position:'absolute', top:0, right:0, width:'48px', height:'48px',
        background:`linear-gradient(225deg, ${accentColor}18 0%, transparent 65%)`,
        pointerEvents:'none', borderRadius:'0 3px 0 0' }} />

      {/* Label row */}
      <div style={{ display:'flex', alignItems:'center',
        justifyContent:'space-between', marginBottom:'10px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:'8px' }}>
          {indicator === 'live' && (
            <div style={{ display:'flex', alignItems:'center', gap:'5px' }}>
              <div className="live-dot" style={{ width:'5px', height:'5px',
                borderRadius:'50%', background:'var(--green)', flexShrink:0 }} />
              <span style={{ fontFamily:'var(--font-mono)', fontSize:'9px',
                color:'var(--green)', letterSpacing:'0.12em' }}>LIVE</span>
            </div>
          )}
          <span style={{ fontFamily:'var(--font-mono)', fontSize:'10px',
            color:'var(--text-muted)', letterSpacing:'0.12em', textTransform:'uppercase' }}>
            {title}
          </span>
          {tooltip && (
            <span className="metric-tip-trigger" tabIndex={0} aria-label={tooltip}>
              <Info size={12} color="var(--text-muted)"
                style={{ cursor:'help', display:'block' }} />
              <span className="metric-tip-box">{tooltip}</span>
            </span>
          )}
        </div>

        {trend && (
          <div style={{ display:'flex', alignItems:'center', gap:'4px',
            padding:'3px 8px',
            background: isUp ? 'var(--green-dim)' : 'var(--red-dim)',
            border:`1px solid ${isUp ? 'rgba(0,230,118,0.2)' : 'rgba(255,23,68,0.2)'}`,
            borderRadius:'2px' }}>
            <span style={{ fontSize:'9px', color: isUp ? 'var(--green)' : 'var(--red)' }}>
              {isUp ? '▲' : '▼'}
            </span>
            <span style={{ fontFamily:'var(--font-mono)', fontSize:'9px',
              color: isUp ? 'var(--green)' : 'var(--red)', letterSpacing:'0.1em' }}>
              {isUp ? 'BULLISH' : 'BEARISH'}
            </span>
          </div>
        )}
      </div>

      {/* Value */}
      <div style={{ fontFamily:'var(--font-mono)', fontSize:'26px', fontWeight:700,
        color:'var(--text-primary)', letterSpacing:'-0.02em', lineHeight:1.1 }}>
        {value}
      </div>

      {/* Sub value */}
      {subValue && (
        <div style={{ marginTop:'6px', fontFamily:'var(--font-mono)', fontSize:'11px',
          color:accentColor, letterSpacing:'0.04em' }}>
          {subValue}
        </div>
      )}

      {/* Bottom line */}
      <div style={{ position:'absolute', bottom:0, left:0, right:0, height:'1px',
        background:`linear-gradient(90deg, transparent, ${accentColor}50, transparent)` }} />
    </motion.div>
  );
}