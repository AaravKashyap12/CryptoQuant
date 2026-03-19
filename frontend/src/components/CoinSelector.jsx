import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';

function HexLogo({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="hg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#00d4ff"/>
          <stop offset="100%" stopColor="#0066ff"/>
        </linearGradient>
      </defs>
      <rect width="32" height="32" fill="#080b0f" rx="6"/>
      <polygon points="16,2 27,8.5 27,23.5 16,30 5,23.5 5,8.5" fill="url(#hg)" opacity="0.12"/>
      <polygon points="16,2 27,8.5 27,23.5 16,30 5,23.5 5,8.5" fill="none" stroke="url(#hg)" strokeWidth="1.5"/>
      <line x1="9" y1="12" x2="9" y2="24" stroke="#1a3a5c" strokeWidth="0.8"/>
      <rect x="7" y="15" width="4" height="5" fill="#ff4466" rx="0.5"/>
      <line x1="15" y1="9" x2="15" y2="23" stroke="#1a3a5c" strokeWidth="0.8"/>
      <rect x="13" y="11" width="4" height="7" fill="#00e676" rx="0.5"/>
      <line x1="21" y1="10" x2="21" y2="22" stroke="#1a3a5c" strokeWidth="0.8"/>
      <rect x="19" y="12" width="4" height="9" fill="#00e676" rx="0.5"/>
      <polyline points="9,13 15,11 21,9" fill="none" stroke="#00d4ff" strokeWidth="1.5"/>
      <circle cx="9" cy="13" r="1.2" fill="#00d4ff"/>
      <circle cx="15" cy="11" r="1.2" fill="#00d4ff"/>
      <circle cx="21" cy="9" r="1.2" fill="#00d4ff"/>
    </svg>
  );
}

const COIN_META = {
  BTC: { symbol: '₿', color: '#f7931a', label: 'BITCOIN' },
  ETH: { symbol: 'Ξ', color: '#627eea', label: 'ETHEREUM' },
  BNB: { symbol: 'B', color: '#f3ba2f', label: 'BNB' },
  SOL: { symbol: '◎', color: '#9945ff', label: 'SOLANA' },
  ADA: { symbol: '₳', color: '#0033ad', label: 'CARDANO' },
};

export function CoinSelector({ coins, selectedCoin, onSelect, livePrice, change24h }) {
  const [open, setOpen] = useState(false);
  const meta = COIN_META[selectedCoin] || { symbol: '●', color: '#00d4ff', label: selectedCoin };
  const isUp = (change24h ?? 0) >= 0;

  return (
    <header className="sticky top-0 z-50" style={{ background: 'rgba(8,11,15,0.95)', backdropFilter: 'blur(12px)', borderBottom: '1px solid var(--border)' }}>

      {/* ── Ticker tape ── */}
      <div style={{ background: 'var(--bg-panel)', borderBottom: '1px solid var(--border)', height: '24px', overflow: 'hidden', position: 'relative' }}>
        <div className="ticker-inner" style={{ display: 'flex', whiteSpace: 'nowrap', gap: '0', height: '100%' }}>
          {[...Array(4)].map((_, pass) =>
            ['BTC','ETH','BNB','SOL','ADA', 'BTC','ETH','BNB','SOL','ADA'].map((c, i) => (
              <span key={`${pass}-${i}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '0 24px', height: '100%', borderRight: '1px solid var(--border)', fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-secondary)', letterSpacing: '0.06em' }}>
                <span style={{ color: COIN_META[c]?.color || 'var(--accent)' }}>{c}/USDT</span>
                <span style={{ color: 'var(--text-muted)' }}>●</span>
              </span>
            ))
          )}
        </div>
        {/* Fade edges */}
        <div style={{ position: 'absolute', top: 0, left: 0, width: '60px', height: '100%', background: 'linear-gradient(90deg, var(--bg-panel), transparent)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', top: 0, right: 0, width: '60px', height: '100%', background: 'linear-gradient(270deg, var(--bg-panel), transparent)', pointerEvents: 'none' }} />
      </div>

      {/* ── Main nav bar ── */}
      <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '52px' }}>

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <HexLogo size={32} />
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '0.12em' }}>
              CRYPTOQUANT
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.2em' }}>
              ANALYTICS TERMINAL v2.0
            </div>
          </div>
        </div>

        {/* Center — live price display */}
        {livePrice && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontFamily: 'var(--font-mono)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div className="live-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--green)' }} />
              <span style={{ fontSize: '10px', color: 'var(--green)', letterSpacing: '0.1em' }}>LIVE</span>
            </div>
            <span style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' }} className={isUp ? 'glow-text-green' : 'glow-text-red'}>
              ${livePrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
            <span style={{ fontSize: '12px', color: isUp ? 'var(--green)' : 'var(--red)', fontWeight: 500 }}>
              {isUp ? '▲' : '▼'} {Math.abs(change24h ?? 0).toFixed(2)}%
            </span>
          </div>
        )}

        {/* Coin selector */}
        <div style={{ position: 'relative' }}>
          <motion.button
            whileHover={{ borderColor: 'var(--accent)' }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setOpen(!open)}
            style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'var(--bg-card)', border: '1px solid var(--border-bright)', borderRadius: '3px', padding: '7px 14px', cursor: 'pointer', minWidth: '160px', justifyContent: 'space-between' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '16px', color: meta.color }}>{meta.symbol}</span>
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '0.06em' }}>{selectedCoin}/USDT</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>{meta.label}</div>
              </div>
            </div>
            <ChevronDown size={14} color="var(--text-muted)" style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
          </motion.button>

          <AnimatePresence>
            {open && (
              <motion.div
                initial={{ opacity: 0, y: -8, scaleY: 0.9 }}
                animate={{ opacity: 1, y: 0, scaleY: 1 }}
                exit={{ opacity: 0, y: -8, scaleY: 0.9 }}
                transition={{ duration: 0.15 }}
                style={{ position: 'absolute', right: 0, top: 'calc(100% + 4px)', background: 'var(--bg-card)', border: '1px solid var(--border-bright)', borderRadius: '3px', minWidth: '200px', overflow: 'hidden', boxShadow: '0 16px 40px rgba(0,0,0,0.6)', zIndex: 100, transformOrigin: 'top' }}
              >
                {/* Header */}
                <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)', fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.15em' }}>
                  SELECT INSTRUMENT
                </div>
                {(coins.length > 0 ? coins : ['BTC','ETH','BNB','SOL','ADA']).map(c => {
                  const m = COIN_META[c] || {};
                  const isSelected = c === selectedCoin;
                  return (
                    <button
                      key={c}
                      onClick={() => { onSelect(c); setOpen(false); }}
                      style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: isSelected ? 'rgba(0,212,255,0.06)' : 'transparent', border: 'none', cursor: 'pointer', borderLeft: isSelected ? '2px solid var(--accent)' : '2px solid transparent', transition: 'all 0.1s' }}
                      onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'var(--bg-hover)'; }}
                      onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontSize: '14px', color: m.color, width: '18px', textAlign: 'center' }}>{m.symbol}</span>
                        <div style={{ textAlign: 'left' }}>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: isSelected ? 600 : 400, color: isSelected ? 'var(--accent)' : 'var(--text-primary)' }}>{c}/USDT</div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>{m.label}</div>
                        </div>
                      </div>
                      {isSelected && <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)', boxShadow: '0 0 8px var(--accent)' }} />}
                    </button>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}