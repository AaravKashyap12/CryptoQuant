import React, { useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const actual    = payload.find(p => p.dataKey === 'Actual')?.value;
  const predicted = payload.find(p => p.dataKey === 'Predicted')?.value;
  const diff = actual && predicted ? Math.abs(actual - predicted) : null;
  const diffPct = actual && diff ? (diff / actual * 100).toFixed(2) : null;

  return (
    <div style={{ background: '#060e18', border: '1px solid var(--border-bright)', borderRadius: '3px', padding: '10px 14px', fontFamily: 'var(--font-mono)', fontSize: '11px', boxShadow: '0 8px 24px rgba(0,0,0,0.7)' }}>
      <div style={{ color: 'var(--text-muted)', fontSize: '9px', letterSpacing: '0.1em', marginBottom: '8px' }}>{label}</div>
      {actual != null && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', color: 'var(--accent)', marginBottom: '3px' }}>
          <span>ACTUAL</span>
          <span>${Number(actual).toLocaleString(undefined, { minimumFractionDigits: 0 })}</span>
        </div>
      )}
      {predicted != null && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', color: 'var(--yellow)' }}>
          <span>PREDICTED</span>
          <span>${Number(predicted).toLocaleString(undefined, { minimumFractionDigits: 0 })}</span>
        </div>
      )}
      {diffPct && (
        <div style={{ marginTop: '6px', paddingTop: '6px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '10px' }}>
          <span>ERROR</span>
          <span>{diffPct}%</span>
        </div>
      )}
    </div>
  );
};

export function ValidationChart({ data }) {
  const { chartData, avgError } = useMemo(() => {
    if (!data?.length) return { chartData: [], avgError: null };
    const cd = data.map(d => ({
      date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      Actual:    d.actual    ?? 0,
      Predicted: d.predicted ?? 0,
    }));
    const errors = data.map(d => d.actual ? Math.abs((d.actual - d.predicted) / d.actual * 100) : 0);
    const avg = errors.reduce((a, b) => a + b, 0) / errors.length;
    return { chartData: cd, avgError: avg.toFixed(2) };
  }, [data]);

  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
        NO VALIDATION DATA
      </div>
    );
  }

  return (
    <div>
      {/* Stats row */}
      {avgError && (
        <div style={{ display: 'flex', gap: '16px', marginBottom: '16px', flexWrap: 'wrap' }}>
          <div style={{ padding: '8px 14px', background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: '3px' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: '4px' }}>AVG ERROR</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 600, color: parseFloat(avgError) < 3 ? 'var(--green)' : parseFloat(avgError) < 6 ? 'var(--yellow)' : 'var(--red)' }}>
              {avgError}%
            </div>
          </div>
          <div style={{ padding: '8px 14px', background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: '3px' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: '4px' }}>SAMPLE SIZE</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 600, color: 'var(--accent)' }}>{data.length}D</div>
          </div>
        </div>
      )}

      <div style={{ height: '280px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 4, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="gradActual" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#00d4ff" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradPred" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#ffd600" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#ffd600" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--border)" strokeDasharray="1 4" vertical={false} />
            <XAxis dataKey="date" stroke="transparent" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }} tickLine={false} axisLine={false} minTickGap={32} />
            <YAxis stroke="transparent" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }} tickLine={false} axisLine={false} domain={['auto', 'auto']} tickFormatter={v => `$${v >= 10000 ? (v/1000).toFixed(0)+'k' : v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} width={44} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="Actual"    stroke="var(--accent)" strokeWidth={1.5} fill="url(#gradActual)" dot={false} />
            <Area type="monotone" dataKey="Predicted" stroke="var(--yellow)" strokeWidth={1.5} strokeDasharray="4 3" fill="url(#gradPred)" dot={false} />
            <Legend
              wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.1em', paddingTop: '12px' }}
              formatter={(value) => value.toUpperCase()}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}