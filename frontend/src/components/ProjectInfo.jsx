import React from 'react';
import { X, Info, AlertTriangle, Cpu, TrendingUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function ProjectInfo({ isOpen, onClose }) {
    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                />

                <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: 20 }}
                    className="bg-[#1e1e1e] border border-[#333] w-full max-w-2xl rounded-2xl shadow-2xl relative overflow-hidden flex flex-col max-h-[90vh]"
                >
                    {/* Header */}
                    <div className="flex justify-between items-center p-6 border-b border-[#333]">
                        <h2 className="text-xl font-bold text-white flex items-center gap-3">
                            <Info className="text-blue-500" />
                            About This Project
                        </h2>
                        <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                            <X size={24} />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="p-8 overflow-y-auto space-y-8">
                        {/* How it Works */}
                        <section>
                            <h3 className="text-lg font-semibold text-yellow-500 mb-4 flex items-center gap-2">
                                <Cpu size={20} />
                                How It Works
                            </h3>
                            <div className="space-y-4 text-gray-300 text-sm leading-relaxed">
                                <p>
                                    This application utilizes a sophisticated <strong>Long Short-Term Memory (LSTM)</strong> neural network to analyze historical cryptocurrency price data.
                                </p>
                                <ul className="list-disc pl-5 space-y-2 marker:text-yellow-500">
                                    <li>
                                        <strong>Data Collection:</strong> We fetch real-time OHLCV (Open, High, Low, Close, Volume) data from major exchanges via the Binance API.
                                    </li>
                                    <li>
                                        <strong>Feature Engineering:</strong> The raw data is processed to calculate technical indicators such as RSI, MACD, and Bollinger Bands, which serve as inputs for the model.
                                    </li>
                                    <li>
                                        <strong>Predictive Modeling:</strong> The LSTM network, trained on years of historical data, identifies temporal patterns and sequential dependencies to forecast future price movements.
                                    </li>
                                    <li>
                                        <strong>Uncertainty Estimation:</strong> We calculate a dynamic confidence interval based on current market volatility to provide a realistic "Spread" of potential outcomes (High/Low estimates).
                                    </li>
                                </ul>
                            </div>
                        </section>

                        {/* Objectives */}
                        <section>
                            <h3 className="text-lg font-semibold text-green-500 mb-4 flex items-center gap-2">
                                <TrendingUp size={20} />
                                Project Goal
                            </h3>
                            <p className="text-gray-300 text-sm leading-relaxed">
                                The goal of this project is to demonstrate the application of deep learning techniques in financial time-series analysis. It serves as a tool for <strong>quantitative exploration</strong> rather than a definitive trading signal generator.
                            </p>
                        </section>

                        {/* Disclaimer */}
                        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
                            <h3 className="text-red-400 font-bold mb-2 flex items-center gap-2">
                                <AlertTriangle size={18} />
                                Important Disclaimer
                            </h3>
                            <p className="text-red-200/80 text-xs">
                                <strong>NOT FINANCIAL ADVICE:</strong> The predictions generated by this model are for educational and informational purposes only. Cryptocurrency markets are highly volatile and unpredictable. Do not trade based solely on these algorithmic outputs. The creators assume no responsibility for any financial losses incurred.
                            </p>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="p-6 border-t border-[#333] bg-[#1a1a1a]">
                        <button
                            onClick={onClose}
                            className="w-full py-3 bg-white text-black font-bold rounded-xl hover:bg-gray-200 transition-colors"
                        >
                            Understood
                        </button>
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
}
