import React from 'react';
import { Activity, AlertCircle, CheckCircle2 } from 'lucide-react';

function formatValue(signal) {
  if (!signal || signal.value == null) return '-';
  const value = Number(signal.value);
  if (!Number.isFinite(value)) return '-';

  if (signal.unit === 'USD') {
    const abs = Math.abs(value);
    if (abs >= 1_000_000_000) return `${value < 0 ? '-' : ''}$${(abs / 1_000_000_000).toFixed(2)}B`;
    if (abs >= 1_000_000) return `${value < 0 ? '-' : ''}$${(abs / 1_000_000).toFixed(2)}M`;
    if (abs >= 1_000) return `${value < 0 ? '-' : ''}$${(abs / 1_000).toFixed(1)}K`;
    return `${value < 0 ? '-' : ''}$${abs.toFixed(0)}`;
  }

  if (signal.unit === 'ratio' || signal.unit === 'z') {
    return value.toFixed(2);
  }

  if (signal.unit === 'percent') {
    return `${value >= 0 ? '+' : ''}${value.toFixed(4)}%`;
  }

  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function changeText(signal) {
  if (signal?.change_7d_pct == null || !Number.isFinite(Number(signal.change_7d_pct))) return 'latest';
  const change = Number(signal.change_7d_pct);
  return `${change >= 0 ? '+' : ''}${change.toFixed(1)}% 7d`;
}

function signalColor(key, signal) {
  const value = Number(signal?.value);
  if (!Number.isFinite(value)) return 'var(--text-primary)';
  if (key === 'exchange_netflow') return value <= 0 ? 'var(--green)' : 'var(--red)';
  if (key === 'sopr') return value >= 1 ? 'var(--green)' : 'var(--red)';
  if (key === 'mvrv_z_score') return value > 6 ? 'var(--red)' : value < 1 ? 'var(--green)' : 'var(--yellow)';
  return 'var(--accent)';
}

function OnChainRow({ label, value, sub, color, shimmer }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px',
        padding: '10px 14px',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '9px',
            color: 'var(--text-muted)',
            letterSpacing: '0.12em',
            marginBottom: '3px',
          }}
        >
          {label}
        </div>
        {shimmer ? (
          <div className="shimmer-skeleton" style={{ width: '86px', height: '14px' }} />
        ) : (
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '14px',
              fontWeight: 600,
              color: color || 'var(--text-primary)',
            }}
          >
            {value}
          </div>
        )}
      </div>
      {sub && !shimmer && (
        <div
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '9px',
            color: 'var(--text-muted)',
            textAlign: 'right',
            letterSpacing: '0.06em',
            lineHeight: 1.5,
            maxWidth: '110px',
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

export function OnChainPanel({ coin, data, loading }) {
  const status = data?.status || (loading ? 'loading' : 'not_configured');
  const isLive = status === 'live';
  const signals = data?.signals || {};
  const isFreeProvider = ['binance-public', 'bybit-public', 'coingecko-public'].includes(data?.provider);

  const premiumRows = [
    ['exchange_netflow', 'EXCHANGE NETFLOW', 'Positive = exchange inflow'],
    ['active_addresses_7d', 'ACTIVE ADDRESSES', 'Network demand proxy'],
    ['sopr', 'SOPR', 'Profit-taking pressure'],
    ['mvrv_z_score', 'MVRV Z-SCORE', 'Valuation heat'],
    ['miner_outflows', 'MINER OUTFLOWS', coin === 'BTC' ? 'Miner sell pressure' : 'BTC only'],
  ];
  const freeRows = [
    ['funding_rate', 'FUNDING RATE', 'Positive = longs pay shorts'],
    ['open_interest_usd', 'OI VALUE', 'Notional futures exposure'],
    ['long_short_ratio', 'LONG / SHORT', 'Account positioning'],
    data?.provider === 'binance-public'
      ? ['taker_buy_sell_ratio', 'TAKER BUY/SELL', 'Aggressive flow proxy']
      : ['volume_24h', '24H TURNOVER', 'Derivatives turnover proxy'],
    ['open_interest', 'OPEN INTEREST', 'Open futures contracts'],
  ];
  const rows = isFreeProvider ? freeRows : premiumRows;
  const displayedSignalCount = rows.filter(([key]) => signals[key]).length;

  const badge = isLive ? (isFreeProvider ? 'FREE LIVE' : 'LIVE') : status === 'unsupported' ? 'N/A' : status === 'loading' ? 'SYNCING' : 'SET API KEY';
  const badgeColor = isLive ? 'var(--green)' : status === 'unsupported' ? 'var(--text-muted)' : 'var(--yellow)';
  const Icon = isLive ? CheckCircle2 : AlertCircle;

  return (
    <div className="t-card on-chain-card" style={{ overflow: 'hidden' }}>
      <div
        style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Activity size={14} color="var(--accent)" />
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              color: 'var(--text-secondary)',
              letterSpacing: '0.12em',
            }}
          >
            {isFreeProvider ? 'FREE MARKET SIGNALS' : 'ON-CHAIN SIGNALS'}
          </span>
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '2px 8px',
            background: 'rgba(0,212,255,0.07)',
            border: '1px solid rgba(0,212,255,0.18)',
            borderRadius: '2px',
            flex: '0 0 auto',
          }}
        >
          <Icon size={10} color={badgeColor} />
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '9px',
              color: badgeColor,
              letterSpacing: '0.1em',
            }}
          >
            {badge}
          </span>
        </div>
      </div>

      <div>
        {rows.map(([key, label, fallback]) => {
          const signal = signals[key];
          const hidden = !isFreeProvider && key === 'miner_outflows' && coin !== 'BTC';
          return (
            <OnChainRow
              key={key}
              label={label}
              value={hidden ? '-' : formatValue(signal)}
              sub={hidden ? fallback : signal?.description || fallback}
              color={signalColor(key, signal)}
              shimmer={status === 'loading'}
            />
          );
        })}
      </div>

      <div
        style={{
          padding: '10px 14px',
          background: 'rgba(0,212,255,0.025)',
          borderTop: '1px solid var(--border)',
        }}
      >
        <p
          style={{
            margin: 0,
            fontFamily: 'var(--font-mono)',
            fontSize: '9px',
            color: 'var(--text-muted)',
            lineHeight: 1.6,
            letterSpacing: '0.04em',
          }}
        >
          {isLive
            ? `${data.provider?.toUpperCase() || 'SIGNAL'} synced. ${displayedSignalCount} signal(s), ${isFreeProvider ? 'free derivatives proxies, not wallet-level on-chain.' : `${changeText(signals.active_addresses_7d)} active-address trend.`}`
            : data?.message || 'Set GLASSNODE_API_KEY on the backend to enable live BTC and ETH on-chain signals.'}
        </p>
      </div>
    </div>
  );
}
