import React from 'react';
import { motion } from 'framer-motion';
import { Github, Linkedin } from 'lucide-react';

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
      <line x1="9"  y1="12" x2="9"  y2="24" stroke="#1a3a5c" strokeWidth="0.8"/>
      <rect x="7"  y="15" width="4" height="5" fill="#ff4466" rx="0.5"/>
      <line x1="15" y1="9"  x2="15" y2="23" stroke="#1a3a5c" strokeWidth="0.8"/>
      <rect x="13" y="11" width="4" height="7" fill="#00e676" rx="0.5"/>
      <line x1="21" y1="10" x2="21" y2="22" stroke="#1a3a5c" strokeWidth="0.8"/>
      <rect x="19" y="12" width="4" height="9" fill="#00e676" rx="0.5"/>
      <polyline points="9,13 15,11 21,9" fill="none" stroke="#00d4ff" strokeWidth="1.5"/>
      <circle cx="9"  cy="13" r="1.2" fill="#00d4ff"/>
      <circle cx="15" cy="11" r="1.2" fill="#00d4ff"/>
      <circle cx="21" cy="9"  r="1.2" fill="#00d4ff"/>
    </svg>
  );
}

// X (Twitter) icon as inline SVG since lucide's is outdated
function XIcon({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.261 5.636 5.902-5.636Zm-1.161 17.52h1.833L7.084 4.126H5.117Z"/>
    </svg>
  );
}

const COIN_META = {
  BTC: { symbol: '\u20bf', color: '#f7931a', label: 'BITCOIN'  },
  ETH: { symbol: '\u039e', color: '#627eea', label: 'ETHEREUM' },
  BNB: { symbol: 'B', color: '#f3ba2f', label: 'BNB'      },
  SOL: { symbol: '\u25ce', color: '#9945ff', label: 'SOLANA'   },
  ADA: { symbol: '\u20b3', color: '#0033ad', label: 'CARDANO'  },
};

const LINKEDIN_URL = 'https://www.linkedin.com/in/aaravkashyapsingh/';

function externalUrl(value, fallback, provider) {
  const raw = String(value || '').trim();

  if (provider === 'linkedin' && raw.includes('aaravkashyapsingh')) {
    return LINKEDIN_URL;
  }

  if (!raw) return fallback;
  if (/^https?:\/\//i.test(raw)) return raw;
  if (/^(www\.|github\.com|linkedin\.com|x\.com)/i.test(raw)) {
    return `https://${raw}`;
  }
  return fallback;
}

// Social rail
function SocialRail() {
  const links = [
    {
      label: 'GitHub',
      href: externalUrl(import.meta.env.VITE_GITHUB_URL, 'https://github.com/AaravKashyap12', 'github'),
      icon:  <Github size={12} strokeWidth={1.8} />,
    },
    {
      label: 'LinkedIn',
      href: externalUrl(import.meta.env.VITE_LINKEDIN_URL, LINKEDIN_URL, 'linkedin'),
      icon:  <Linkedin size={12} strokeWidth={1.8} />,
    },
    {
      label: 'X',
      href: externalUrl(import.meta.env.VITE_X_URL, 'https://x.com/byaarav', 'x'),
      icon:  <XIcon size={11} />,
    },
  ];

  return (
    <div style={{
      borderBottom: '1px solid rgba(0,212,255,0.15)',
      background: 'linear-gradient(90deg, rgba(0,212,255,0.06) 0%, transparent 40%, rgba(247,147,26,0.05) 100%)',
    }}>
      <div style={{
        maxWidth: '1440px', margin: '0 auto', padding: '0 24px',
        height: '34px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', gap: '16px',
        fontFamily: 'var(--font-mono)',
      }}>
        {/* Author */}
        <div style={{ display:'flex', alignItems:'center', gap:'10px', minWidth:0 }}>
          <span style={{ width:'6px', height:'6px', borderRadius:'50%',
            background:'var(--accent)', boxShadow:'0 0 10px var(--accent)',
            flexShrink:0, display:'block' }} aria-hidden />
          <span style={{ fontSize:'9px', color:'var(--text-muted)', letterSpacing:'0.18em' }}>
            BUILT BY
          </span>
          <span style={{ fontSize:'11px', color:'var(--text-primary)',
            letterSpacing:'0.14em', whiteSpace:'nowrap' }}>
            AARAV KASHYAP
          </span>
        </div>

        {/* Social links */}
        <nav aria-label="Creator links"
          style={{ display:'flex', alignItems:'center', gap:'6px', flexShrink:0 }}>
          {links.map(({ label, href, icon }) => (
            <a
              key={label}
              href={href}
              target="_blank"
              rel="noreferrer"
              aria-label={label}
              title={label}
              style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                gap: '5px', height: '22px', padding: '0 9px',
                border: '1px solid rgba(0,212,255,0.22)',
                background: 'rgba(13,17,23,0.8)',
                color: 'var(--text-secondary)',
                textDecoration: 'none', borderRadius: '2px',
                fontFamily: 'var(--font-mono)', fontSize: '9px',
                letterSpacing: '0.08em', lineHeight: 1,
                transition: 'color 140ms, border-color 140ms, background 140ms',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.color = 'var(--accent)';
                e.currentTarget.style.borderColor = 'rgba(0,212,255,0.5)';
                e.currentTarget.style.background = 'rgba(0,212,255,0.07)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.color = 'var(--text-secondary)';
                e.currentTarget.style.borderColor = 'rgba(0,212,255,0.22)';
                e.currentTarget.style.background = 'rgba(13,17,23,0.8)';
              }}
            >
              {icon}
              {label !== 'X' && <span>{label.toUpperCase()}</span>}
            </a>
          ))}
        </nav>
      </div>
    </div>
  );
}

// Coin selector
export function CoinSelector({ coins, selectedCoin, onSelect, livePrice, change24h }) {
  const isUp = (change24h ?? 0) >= 0;
  const coinList = coins.length > 0 ? coins : ['BTC','ETH','BNB','SOL','ADA'];

  return (
    <header
      className="sticky top-0 z-50"
      style={{
        background: 'rgba(8,11,15,0.82)',
        backdropFilter: 'blur(18px) saturate(125%)',
        WebkitBackdropFilter: 'blur(18px) saturate(125%)',
        borderBottom: '1px solid rgba(0,212,255,0.18)',
        boxShadow: '0 16px 50px rgba(0,0,0,0.28)',
      }}
    >
      <SocialRail />

      {/* Ticker tape */}
      <div style={{ background:'rgba(13,17,23,0.62)', borderBottom:'1px solid rgba(26,40,64,0.82)',
        height:'22px', overflow:'hidden', position:'relative' }}>
        <div className="ticker-inner"
          style={{ display:'flex', whiteSpace:'nowrap', height:'100%' }}>
          {[...Array(6)].map((_, pass) =>
            ['BTC','ETH','BNB','SOL','ADA'].map((c, i) => (
              <span key={`${pass}-${i}`} style={{
                display:'inline-flex', alignItems:'center', gap:'6px',
                padding:'0 20px', height:'100%',
                borderRight:'1px solid var(--border)',
                fontFamily:'var(--font-mono)', fontSize:'9px',
                color:'var(--text-muted)', letterSpacing:'0.06em',
              }}>
                <span style={{ color: COIN_META[c]?.color || 'var(--accent)' }}>{c}/USDT</span>
                <span style={{ color:'var(--text-muted)', fontSize:'7px' }}>{'\u25c6'}</span>
              </span>
            ))
          )}
        </div>
        <div style={{ position:'absolute', top:0, left:0, width:'48px', height:'100%',
          background:'linear-gradient(90deg, var(--bg-panel), transparent)', pointerEvents:'none' }} />
        <div style={{ position:'absolute', top:0, right:0, width:'48px', height:'100%',
          background:'linear-gradient(270deg, var(--bg-panel), transparent)', pointerEvents:'none' }} />
      </div>

      {/* Main nav */}
      <div style={{
        maxWidth:'1440px',
        margin:'0 auto',
        padding:'10px 24px',
        display:'flex',
        alignItems:'center',
        justifyContent:'space-between',
        minHeight:'64px',
        gap:'16px',
        flexWrap:'wrap',
      }}>

        {/* Logo */}
        <div style={{ display:'flex', alignItems:'center', gap:'12px' }}>
          <HexLogo size={30} />
          <div>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:'13px', fontWeight:600,
              color:'var(--text-primary)', letterSpacing:'0.14em' }}>CRYPTOQUANT</div>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:'8px',
              color:'var(--text-muted)', letterSpacing:'0.22em' }}>ANALYTICS TERMINAL v2.1</div>
          </div>
        </div>

        {/* Center live price */}
        {livePrice > 0 && (
          <div style={{ display:'flex', alignItems:'center', gap:'14px',
            fontFamily:'var(--font-mono)' }}>
            <div style={{ display:'flex', alignItems:'center', gap:'5px' }}>
              <div className="live-dot" style={{ width:'6px', height:'6px',
                borderRadius:'50%', background:'var(--green)' }} />
              <span style={{ fontSize:'9px', color:'var(--green)', letterSpacing:'0.12em' }}>LIVE</span>
            </div>
            <span style={{ fontSize:'20px', fontWeight:700, color:'var(--text-primary)',
              letterSpacing:'-0.02em' }}
              key={livePrice}
              className={`${isUp ? 'glow-text-green price-flash-up' : 'glow-text-red price-flash-down'}`}>
              ${livePrice.toLocaleString(undefined, { minimumFractionDigits:2 })}
            </span>
            <span style={{ fontSize:'12px', fontWeight:500,
              color: isUp ? 'var(--green)' : 'var(--red)' }}>
              {isUp ? '\u25b2' : '\u25bc'} {Math.abs(change24h ?? 0).toFixed(2)}%
            </span>
          </div>
        )}

        <div className="coin-pill-row" aria-label="Select market">
          {coinList.map((coin, index) => {
            const meta = COIN_META[coin] || { symbol: '\u25cf', color: '#00d4ff', label: coin };
            const active = coin === selectedCoin;
            return (
              <motion.button
                key={coin}
                type="button"
                className={`coin-pill ${active ? 'active' : ''}`}
                onClick={() => onSelect(coin)}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.12 + index * 0.035, duration: 0.34 }}
                whileHover={{ y: -2 }}
                whileTap={{ scale: 0.97 }}
                aria-pressed={active}
                title={meta.label}
              >
                <span className="coin-pill-symbol" style={{ color: meta.color }}>{meta.symbol}</span>
                <span>{coin}</span>
              </motion.button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
