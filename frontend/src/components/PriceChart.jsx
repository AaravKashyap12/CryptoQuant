import React, { useMemo, useState } from 'react';
import {
  ComposedChart, Line, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';

const TIME_RANGES = ['7D', '1M', '3M', '1Y', 'All'];

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  const isForecast = d.type === 'forecast';

  return (
    <div style={{ background: '#060e18', border: '1px solid var(--border-bright)', borderRadius: '3px', padding: '12px 14px', minWidth: '190px', boxShadow: '0 8px 32px rgba(0,0,0,0.8)', fontFamily: 'var(--font-mono)' }}>
      <div style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>{d.date}</span>
        {isForecast && (
          <span style={{ background: 'rgba(255,214,0,0.12)', border: '1px solid rgba(255,214,0,0.3)', color: 'var(--yellow)', padding: '1px 6px', fontSize: '9px', letterSpacing: '0.1em' }}>FORECAST</span>
        )}
      </div>
      <div style={{ fontSize: '20px', fontWeight: 600, color: isForecast ? 'var(--yellow)' : 'var(--text-primary)', letterSpacing: '-0.02em' }}>
        ${Number(d.price).toLocaleString(undefined, { minimumFractionDigits: 2 })}
      </div>
      {isForecast && d.upper != null && (
        <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px' }}>
            <span style={{ color: 'var(--text-muted)' }}>95th pct</span>
            <span style={{ color: 'var(--green)' }}>${Number(d.upper).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px' }}>
            <span style={{ color: 'var(--text-muted)' }}>5th pct</span>
            <span style={{ color: 'var(--red)' }}>${Number(d.lower).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', marginTop: '2px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Spread</span>
            <span style={{ color: 'var(--accent)' }}>±{(((d.upper - d.lower) / d.price) * 50).toFixed(1)}%</span>
          </div>
        </div>
      )}
    </div>
  );
};

export function PriceChart({ data, forecast, coin }) {
  const [timeRange, setTimeRange] = useState('3M'); // default to 3M for cleaner first load

  const { chartData, minPrice, maxPrice, priceChange } = useMemo(() => {
    if (!data?.length) return { chartData: [], minPrice: 0, maxPrice: 0, priceChange: 0 };

    const historical = data.map(d => ({
      date:     new Date(Number(d.open_time)).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      fullDate: new Date(Number(d.open_time)),
      price:    d.close,
      type:     'historical',
    }));

    let filtered = historical;
    if (timeRange !== 'All') {
      const cutoff = new Date();
      if (timeRange === '7D')  cutoff.setDate(cutoff.getDate() - 7);
      if (timeRange === '1M')  cutoff.setMonth(cutoff.getMonth() - 1);
      if (timeRange === '3M')  cutoff.setMonth(cutoff.getMonth() - 3);
      if (timeRange === '1Y')  cutoff.setFullYear(cutoff.getFullYear() - 1);
      filtered = historical.filter(d => d.fullDate >= cutoff);
    }

    let combined = filtered;
    if (forecast?.mean?.length) {
      const lastDate = historical[historical.length - 1].fullDate;
      const fPoints = forecast.mean.map((val, i) => {
        const d = new Date(lastDate);
        d.setDate(d.getDate() + i + 1);
        return { date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), fullDate: d, price: val, upper: forecast.upper[i], lower: forecast.lower[i], type: 'forecast' };
      });
      combined = [...filtered, ...fPoints];
    }

    const prices = combined.map(d => d.price).filter(Boolean);
    const minP = Math.min(...prices) * 0.998;
    const maxP = Math.max(...prices) * 1.002;

    const firstPrice = filtered[0]?.price || 0;
    const lastPrice  = filtered[filtered.length - 1]?.price || 0;
    const change = firstPrice ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0;

    return { chartData: combined, minPrice: minP, maxPrice: maxP, priceChange: change };
  }, [data, forecast, timeRange]);

  const isUp = priceChange >= 0;
  const lineColor = isUp ? 'var(--green)' : 'var(--red)';
  const gradId = isUp ? 'gradUp' : 'gradDown';
  const gradColor = isUp ? '#00e676' : '#ff1744';

  if (!data?.length) {
    return (
      <div style={{ height: '420px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px', letterSpacing: '0.1em' }}>
        <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-bright)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        LOADING MARKET DATA...
      </div>
    );
  }

  return (
    <div>
      {/* Chart header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', padding: '0 4px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.15em' }}>PRICE ACTION</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '2px 8px', background: isUp ? 'var(--green-dim)' : 'var(--red-dim)', borderRadius: '2px' }}>
            <span style={{ fontSize: '10px', color: isUp ? 'var(--green)' : 'var(--red)', fontFamily: 'var(--font-mono)' }}>
              {isUp ? '▲' : '▼'} {Math.abs(priceChange).toFixed(2)}%
            </span>
          </div>
          {forecast && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '16px', height: '1px', background: 'var(--yellow)', borderTop: '1px dashed var(--yellow)' }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>7D FORECAST</span>
            </div>
          )}
        </div>

        {/* Time range */}
        <div style={{ display: 'flex', gap: '2px' }}>
          {TIME_RANGES.map(r => (
            <button key={r} onClick={() => setTimeRange(r)} className={`t-btn ${timeRange === r ? 'active' : ''}`}>
              {r}
            </button>
          ))}
        </div>
      </div>

      <div style={{ height: '400px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 8, right: 60, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="gradUp" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#00e676" stopOpacity={0.18} />
                <stop offset="100%" stopColor="#00e676" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradDown" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#ff1744" stopOpacity={0.14} />
                <stop offset="100%" stopColor="#ff1744" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradForecast" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#ffd600" stopOpacity={0.12} />
                <stop offset="100%" stopColor="#ffd600" stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid stroke="var(--border)" strokeDasharray="1 3" vertical={false} />

            <XAxis dataKey="date" stroke="transparent" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }} tickLine={false} axisLine={false} minTickGap={48} />
            <YAxis domain={[minPrice, maxPrice]} orientation="right" stroke="transparent" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }} tickLine={false} axisLine={false} tickFormatter={v => `$${v >= 10000 ? (v/1000).toFixed(0)+'k' : v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} width={58} />

            <Tooltip content={<CustomTooltip />} />

            {/* Confidence band */}
            <Area dataKey="upper" stroke="none" fill="#ffd600" fillOpacity={0.06} dot={false} activeDot={false} connectNulls isAnimationActive={false} />
            <Area dataKey="lower" stroke="none" fill="var(--bg-card)" fillOpacity={1} dot={false} activeDot={false} connectNulls isAnimationActive={false} />

            {/* Confidence band borders */}
            <Line type="monotone" dataKey="upper" stroke="#ffd600" strokeWidth={0.8} strokeDasharray="2 4" dot={false} activeDot={false} strokeOpacity={0.4} connectNulls />
            <Line type="monotone" dataKey="lower" stroke="#ffd600" strokeWidth={0.8} strokeDasharray="2 4" dot={false} activeDot={false} strokeOpacity={0.4} connectNulls />

            {/* Historical area fill */}
            <Area type="monotone" dataKey={d => d.type === 'historical' ? d.price : null} stroke="none" fill={`url(#${gradId})`} dot={false} activeDot={false} connectNulls isAnimationActive={false} />

            {/* Historical line */}
            <Line type="monotone" dataKey={d => d.type === 'historical' ? d.price : null}
              stroke={lineColor} strokeWidth={1.5} dot={false}
              activeDot={{ r: 4, fill: lineColor, strokeWidth: 0 }}
              connectNulls name="Price" animationDuration={1000}
            />

            {/* Forecast line */}
            <Line type="monotone" dataKey={d => d.type === 'forecast' ? d.price : null}
              stroke="var(--yellow)" strokeWidth={2} strokeDasharray="4 3"
              dot={false} activeDot={{ r: 4, fill: 'var(--yellow)', strokeWidth: 0 }}
              connectNulls name="Forecast" animationDuration={800} animationBegin={700}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}