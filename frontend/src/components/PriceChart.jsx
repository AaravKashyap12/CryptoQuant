import React, { useMemo, useState } from 'react';
import {
    ComposedChart, Line, Area, XAxis, YAxis,
    CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;

    const d = payload[0]?.payload;
    if (!d) return null;
    const isForecast = d.type === 'forecast';

    return (
        <div className="bg-[#0e1117]/95 border border-[#333] p-4 rounded-lg shadow-xl backdrop-blur-sm z-50 min-w-[180px]">
            <p className="text-gray-400 text-xs mb-2">{d.date}</p>
            <div className="flex items-baseline gap-2">
                <p className="text-white font-bold text-lg">
                    ${Number(d.price).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
                {isForecast && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-500 font-medium">FORECAST</span>
                )}
            </div>

            {isForecast && d.upper != null && d.lower != null && (
                <div className="text-xs space-y-1 mt-3 border-t border-[#333] pt-2">
                    <div className="flex justify-between text-green-400">
                        <span className="opacity-80">Upper (95%):</span>
                        <span className="font-mono">${Number(d.upper).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                    </div>
                    <div className="flex justify-between text-red-400">
                        <span className="opacity-80">Lower (5%):</span>
                        <span className="font-mono">${Number(d.lower).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                    </div>
                    <div className="mt-1 text-[10px] text-gray-500 italic text-right">
                        Spread: ±{(((d.upper - d.lower) / d.price) * 50).toFixed(1)}%
                    </div>
                </div>
            )}
        </div>
    );
};

const TIME_RANGES = ['7D', '1M', '3M', '1Y', 'All'];

export function PriceChart({ data, forecast }) {
    const [timeRange, setTimeRange] = useState('3M');

    const chartData = useMemo(() => {
        if (!data?.length) return [];

        const historical = data.map(d => ({
            date:     new Date(Number(d.open_time)).toLocaleDateString(),
            fullDate: new Date(Number(d.open_time)),
            price:    d.close,
            type:     'historical',
        }));

        // Filter by time range
        let filtered = historical;
        if (timeRange !== 'All') {
            const cutoff = new Date();
            if (timeRange === '7D') cutoff.setDate(cutoff.getDate() - 7);
            if (timeRange === '1M') cutoff.setMonth(cutoff.getMonth() - 1);
            if (timeRange === '3M') cutoff.setMonth(cutoff.getMonth() - 3);
            if (timeRange === '1Y') cutoff.setFullYear(cutoff.getFullYear() - 1);
            filtered = historical.filter(d => d.fullDate >= cutoff);
        }

        if (!forecast?.mean?.length) return filtered;

        const lastDate = historical[historical.length - 1].fullDate;
        const forecastPoints = forecast.mean.map((val, i) => {
            const d = new Date(lastDate);
            d.setDate(d.getDate() + i + 1);
            return {
                date:     d.toLocaleDateString(),
                fullDate: d,
                price:    val,
                upper:    forecast.upper[i],
                lower:    forecast.lower[i],
                type:     'forecast',
            };
        });

        return [...filtered, ...forecastPoints];
    }, [data, forecast, timeRange]);

    if (!data?.length) {
        return (
            <div className="h-[400px] flex items-center justify-center text-gray-500 animate-pulse">
                Loading Market Data…
            </div>
        );
    }

    return (
        <div className="w-full">
            {/* Header + range selector */}
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Price Action</h2>
                <div className="flex bg-[#0e1117] rounded-lg p-1 border border-[#333]">
                    {TIME_RANGES.map(r => (
                        <button
                            key={r}
                            onClick={() => setTimeRange(r)}
                            className={`px-3 py-1 text-xs rounded-md transition-all ${
                                timeRange === r ? 'bg-[#2b2b2b] text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'
                            }`}
                        >
                            {r}
                        </button>
                    ))}
                </div>
            </div>

            <div className="h-[450px]">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorHist" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.25} />
                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                            </linearGradient>
                        </defs>

                        <CartesianGrid stroke="#2B2F36" strokeDasharray="3 3" vertical={false} />

                        <XAxis
                            dataKey="date"
                            stroke="#9ca3af"
                            tick={{ fill: '#9ca3af', fontSize: 11 }}
                            tickLine={false}
                            axisLine={false}
                            minTickGap={40}
                        />
                        <YAxis
                            domain={['auto', 'auto']}
                            orientation="right"
                            stroke="#9ca3af"
                            tick={{ fill: '#9ca3af', fontSize: 11 }}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={v => `$${v.toLocaleString()}`}
                        />

                        <Tooltip content={<CustomTooltip />} />

                        {/* Confidence band — only has values on forecast points */}
                        <Area
                            dataKey="upper"
                            stroke="none"
                            fill="#F0B90B"
                            fillOpacity={0.12}
                            dot={false}
                            activeDot={false}
                            connectNulls
                            isAnimationActive={false}
                        />
                        <Area
                            dataKey="lower"
                            stroke="none"
                            fill="#0e1117"   /* fill down to lower to create band effect */
                            fillOpacity={1}
                            dot={false}
                            activeDot={false}
                            connectNulls
                            isAnimationActive={false}
                        />

                        {/* Dashed forecast bound lines */}
                        <Line
                            type="monotone"
                            dataKey="upper"
                            stroke="#F0B90B"
                            strokeWidth={1}
                            strokeDasharray="3 3"
                            dot={false}
                            activeDot={false}
                            strokeOpacity={0.5}
                            connectNulls
                        />
                        <Line
                            type="monotone"
                            dataKey="lower"
                            stroke="#F0B90B"
                            strokeWidth={1}
                            strokeDasharray="3 3"
                            dot={false}
                            activeDot={false}
                            strokeOpacity={0.5}
                            connectNulls
                        />

                        {/* Historical price line */}
                        <Line
                            type="monotone"
                            dataKey={d => d.type === 'historical' ? d.price : null}
                            stroke="#3b82f6"
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 5, fill: '#3b82f6' }}
                            connectNulls
                            name="Price"
                            animationDuration={1200}
                        />

                        {/* Forecast line (dashed, yellow) — only on forecast points */}
                        <Line
                            type="monotone"
                            dataKey={d => d.type === 'forecast' ? d.price : null}
                            stroke="#F0B90B"
                            strokeWidth={2.5}
                            strokeDasharray="5 5"
                            dot={false}
                            activeDot={{ r: 5, fill: '#F0B90B', strokeWidth: 0 }}
                            connectNulls
                            name="Forecast"
                            animationDuration={1200}
                            animationBegin={900}
                        />
                    </ComposedChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
