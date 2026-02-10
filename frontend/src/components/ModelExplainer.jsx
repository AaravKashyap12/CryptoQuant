import React, { useState } from 'react';
import { ChevronDown, ChevronUp, BrainCircuit, TrendingUp, Activity, BarChart3 } from 'lucide-react';

export function ModelExplainer({ trend, analysis }) {
    const [isOpen, setIsOpen] = useState(true);

    // Default analysis if none provided
    const rsi = analysis?.rsi || 50;
    const macd = analysis?.macd || 0;
    const vol = analysis?.volatility || 0;

    let sentiment = "Neutral";
    let color = "text-gray-400";
    if (trend === 'up') { sentiment = "BULLISH"; color = "text-green-500"; }
    if (trend === 'down') { sentiment = "BEARISH"; color = "text-red-500"; }

    return (
        <div className="bg-[#1e1e1e] border border-[#333] rounded-2xl overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex justify-between items-center p-6 hover:bg-[#252525] transition-colors text-left"
            >
                <h2 className="text-lg font-bold flex items-center gap-3">
                    <BrainCircuit className="text-yellow-500" />
                    Model Analysis & Logic
                </h2>
                {isOpen ? <ChevronUp className="text-gray-500" /> : <ChevronDown className="text-gray-500" />}
            </button>

            {isOpen && (
                <div className="p-6 pt-0 border-t border-[#333]/50">
                    <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

                        {/* Logic 1: Sentiment */}
                        <div className="space-y-2">
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Overall Sentiment</span>
                            <div className={`text-xl font-bold ${color} flex items-center gap-2`}>
                                {sentiment}
                                {trend === 'up' ? <TrendingUp size={20} /> : <Activity size={20} />}
                            </div>
                            <p className="text-xs text-gray-400 leading-relaxed">
                                The LSTM model has detected a {sentiment.toLowerCase()} pattern over the last 60 days of price action.
                            </p>
                        </div>

                        {/* Logic 2: RSI */}
                        <div className="space-y-2">
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">RSI Momentum</span>
                            <div className="text-xl font-bold text-white flex items-center gap-2">
                                {rsi.toFixed(1)} <span className="text-xs text-gray-500 font-normal">/ 100</span>
                            </div>
                            <p className="text-xs text-gray-400 leading-relaxed">
                                {rsi > 70 ? "Market is OVERBOUGHT. High chance of correction." :
                                    rsi < 30 ? "Market is OVERSOLD. Potential bounce incoming." :
                                        "Market momentum is neutral and stable."}
                            </p>
                        </div>

                        {/* Logic 3: Trend Strength */}
                        <div className="space-y-2">
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Trend Strength (MACD)</span>
                            <div className={`text-xl font-bold ${macd > 0 ? "text-green-400" : "text-red-400"}`}>
                                {macd > 0 ? "Positive" : "Negative"}
                            </div>
                            <p className="text-xs text-gray-400 leading-relaxed">
                                Moving Average Convergence Divergence indicates {macd > 0 ? "buying" : "selling"} pressure is currently dominant.
                            </p>
                        </div>

                        {/* Logic 4: Risk */}
                        <div className="space-y-2">
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Volatility Risk</span>
                            <div className="text-xl font-bold text-white shadow-yellow-500/20">
                                ${vol.toFixed(2)}
                            </div>
                            <p className="text-xs text-gray-400 leading-relaxed">
                                Average daily price movement. Higher volatility means wider confidence intervals in the forecast.
                            </p>
                        </div>

                    </div>

                    <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl flex items-start gap-3">
                        <InfoIcon className="text-blue-400 shrink-0 mt-0.5" size={16} />
                        <p className="text-xs text-blue-200">
                            <strong>How it works:</strong> This prediction uses a 3-layer LSTM Neural Network trained on {new Date().getFullYear() - 2017}+ years of OHLCV data.
                            It does not factor in breaking news, social media sentiment, or on-chain metrics yet.
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}

function InfoIcon({ className, size }) {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" /></svg>
    )
}
