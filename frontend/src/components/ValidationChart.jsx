import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export function ValidationChart({ data }) {
    if (!data || !Array.isArray(data) || data.length === 0) return <div className="text-gray-500 text-sm">No validation data available.</div>;

    const chartData = data.map(d => ({
        date: new Date(d.date).toLocaleDateString(),
        Actual: d.actual !== undefined ? d.actual : 0,
        Predicted: d.predicted !== undefined ? d.predicted : 0,
        diff: Math.abs((d.actual || 0) - (d.predicted || 0))
    }));

    return (
        <div className="h-[300px] w-full mt-4">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                    <defs>
                        <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorPred" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#eab308" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#eab308" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                    <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1E1E1E', borderColor: '#333', color: '#fff' }}
                        itemStyle={{ fontSize: '12px' }}
                        formatter={(value) => [`$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, "Price"]}
                        labelFormatter={(label) => `Date: ${label}`}
                    />
                    <Legend />
                    <Area type="monotone" dataKey="Actual" stroke="#3b82f6" fillOpacity={1} fill="url(#colorActual)" strokeWidth={2} />
                    <Area type="monotone" dataKey="Predicted" stroke="#eab308" fillOpacity={1} fill="url(#colorPred)" strokeWidth={2} strokeDasharray="5 5" />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
