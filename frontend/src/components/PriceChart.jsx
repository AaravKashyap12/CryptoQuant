import React, { useState } from 'react';
import {
    ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, ReferenceLine, Brush
} from 'recharts';
import { format } from 'date-fns';

const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
        // Find the main price payload (it could be history or forecast)
        const pricePayload = payload.find(p => p.dataKey === 'price' || (p.payload && p.payload.price));
        if (!pricePayload) return null;

        const data = pricePayload.payload;
        const isForecast = data.type === 'forecast';

        return (
            <div className="bg-[#0e1117]/95 border border-[#333] p-4 rounded-lg shadow-xl backdrop-blur-sm z-50">
                <p className="text-gray-400 text-xs mb-2">{label}</p>
                <div className="flex items-baseline gap-2">
                    <p className="text-white font-bold text-lg mb-1">
                        ${(Number(data.price) || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                    {isForecast && <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-500 font-medium">FORECAST</span>}
                </div>

                {isForecast && (
                    <div className="text-xs space-y-1 mt-3 border-t border-[#333] pt-2 w-48">
                        <div className="flex justify-between items-center text-green-400">
                            <span className="opacity-80">High (95% Conf.):</span>
                            <span className="font-mono">${(Number(data.upper) || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                        </div>
                        <div className="flex justify-between items-center text-red-400">
                            <span className="opacity-80">Low (5% Conf.):</span>
                            <span className="font-mono">${(Number(data.lower) || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                        </div>
                        <div className="mt-2 text-[10px] text-gray-500 italic text-right">
                            Spread: ±{(((data.upper - data.lower) / data.price) * 50).toFixed(1)}%
                        </div>
                    </div>
                )}
            </div>
        );
    }
    return null;
};

export function PriceChart({ data, forecast }) {
    const [timeRange, setTimeRange] = useState('3M');

    if (!data || data.length === 0) return (
        <div className="h-[400px] flex items-center justify-center text-gray-500 bg-[#1e1e1e]/50 rounded-xl animate-pulse">
            Loading Market Data...
        </div>
    );

    // Process Data
    const historicalData = data.map(d => ({
        date: new Date(Number(d.open_time)).toLocaleDateString(),
        fullDate: new Date(Number(d.open_time)),
        price: d.close,
        type: 'historical'
    }));

    let chartData = [...historicalData];

    // Filter by TimeRange
    if (timeRange !== 'All') {
        const cutoff = new Date();
        if (timeRange === '7D') cutoff.setDate(cutoff.getDate() - 7);
        if (timeRange === '1M') cutoff.setMonth(cutoff.getMonth() - 1);
        if (timeRange === '3M') cutoff.setMonth(cutoff.getMonth() - 3);
        if (timeRange === '1Y') cutoff.setFullYear(cutoff.getFullYear() - 1);

        chartData = chartData.filter(d => d.fullDate >= cutoff);
    }

    // Add Forecast
    if (forecast && forecast.mean) {
        const lastHistDate = historicalData[historicalData.length - 1].fullDate;

        // Connect last historical point to first forecast point prevents gap
        // Actually Recharts lines connect automatically if nulls are handled, but we are appending.

        const forecastPoints = forecast.mean.map((val, i) => {
            const date = new Date(lastHistDate);
            date.setDate(lastHistDate.getDate() + (i + 1));
            return {
                date: date.toLocaleDateString(),
                fullDate: date,
                price: val,
                lower: forecast.lower[i],
                upper: forecast.upper[i],
                range: [forecast.lower[i], forecast.upper[i]], // For Area
                type: 'forecast'
            };
        });
        chartData = [...chartData, ...forecastPoints];
    }

    return (
        <div className="w-full">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Price Action</h2>
                <div className="flex bg-[#0e1117] rounded-lg p-1 border border-[#333]">
                    {['7D', '1M', '3M', '1Y', 'All'].map(range => (
                        <button
                            key={range}
                            onClick={() => setTimeRange(range)}
                            className={`px-3 py-1 text-xs rounded-md transition-all ${timeRange === range
                                ? 'bg-[#2b2b2b] text-white shadow-sm'
                                : 'text-gray-500 hover:text-gray-300'
                                }`}
                        >
                            {range}
                        </button>
                    ))}
                </div>
            </div>

            <div className="h-[450px]">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                            </linearGradient>
                            <pattern id="striped" x="0" y="0" width="4" height="4" patternUnits="userSpaceOnUse">
                                <line x1="0" y1="0" x2="0" y2="0" stroke="#F0B90B" strokeWidth="1" />
                            </pattern>
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
                            tickFormatter={(val) => `$${val.toLocaleString()}`}
                        />
                        <Tooltip content={<CustomTooltip />} />

                        {/* Confidence Area */}
                        <Area
                            dataKey="range"
                            stroke="none"
                            fill="#F0B90B"
                            fillOpacity={0.2}
                        />

                        {/* Explicit Upper/Lower Bound Lines - Thin & Dashed */}
                        <Line
                            type="monotone"
                            dataKey="upper"
                            stroke="#F0B90B"
                            strokeWidth={1}
                            strokeDasharray="3 3"
                            dot={false}
                            activeDot={false}
                            strokeOpacity={0.5}
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
                        />

                        {/* Historical Line */}
                        <Line
                            type="monotone"
                            dataKey="price"
                            stroke="#3b82f6"
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 6, fill: '#3b82f6' }}
                            animationDuration={1500}
                            connectNulls
                        />

                        {/* Forecast Line (Dashed) */}
                        <Line
                            type="monotone"
                            dataKey={(d) => d.type === 'forecast' ? d.price : null}
                            stroke="#F0B90B"
                            strokeWidth={3}
                            strokeDasharray="5 5"
                            dot={false}
                            activeDot={{ r: 6, fill: '#F0B90B', strokeWidth: 0 }}
                            connectNulls
                            name="Forecast"
                            animationDuration={1500}
                            animationBegin={1000}
                        />

                        {/* Re-render Historical on top ensuring color consistency */}
                        <Line
                            type="monotone"
                            dataKey={(d) => d.type === 'historical' ? d.price : null}
                            stroke="#3b82f6"
                            strokeWidth={2}
                            dot={false}
                            connectNulls
                            name="History"
                        />

                    </ComposedChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
