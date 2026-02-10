import React, { useState } from 'react';
import { Activity, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function CoinSelector({ coins, selectedCoin, onSelect }) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="sticky top-0 z-50 bg-[#0e1117]/80 backdrop-blur-md border-b border-[#333] py-4">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <div className="bg-gradient-to-br from-yellow-400 to-yellow-600 p-2 rounded-lg">
                        <Activity className="text-black" size={24} />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                            CryptoQuant
                        </h1>
                        <p className="text-xs text-gray-500 font-medium tracking-wider">QUANTITATIVE ANALYTICS</p>
                    </div>
                </div>

                <div className="relative">
                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => setIsOpen(!isOpen)}
                        className="flex items-center gap-3 bg-[#1e1e1e] border border-[#333] text-white rounded-xl pl-4 pr-3 py-2 hover:border-yellow-500/30 transition-colors w-40 justify-between"
                    >
                        <span className="font-medium">{selectedCoin} / USDT</span>
                        <ChevronDown size={16} className={`text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                    </motion.button>

                    <AnimatePresence>
                        {isOpen && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                transition={{ duration: 0.2 }}
                                className="absolute right-0 top-full mt-2 w-48 bg-[#1e1e1e] border border-[#333] rounded-xl shadow-xl overflow-hidden z-50"
                            >
                                {coins.map((coin) => (
                                    <button
                                        key={coin}
                                        onClick={() => {
                                            onSelect(coin);
                                            setIsOpen(false);
                                        }}
                                        className={`w-full text-left px-4 py-3 text-sm hover:bg-[#252525] transition-colors ${selectedCoin === coin ? 'text-yellow-500 font-bold bg-yellow-500/5' : 'text-gray-300'
                                            }`}
                                    >
                                        <div className="flex justify-between items-center">
                                            {coin} / USDT
                                            {selectedCoin === coin && <div className="w-1.5 h-1.5 rounded-full bg-yellow-500" />}
                                        </div>
                                    </button>
                                ))}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}
