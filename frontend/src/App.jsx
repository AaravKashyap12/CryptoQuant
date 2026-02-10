import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { getCoins, getMarketData, getPrediction, getMetrics, getValidation } from './lib/api';
import { CoinSelector } from './components/CoinSelector';
import { MetricsCard } from './components/MetricsCard';
import { PriceChart } from './components/PriceChart';
import { ModelExplainer } from './components/ModelExplainer';
import { ProjectInfo } from './components/ProjectInfo';
import { ValidationChart } from './components/ValidationChart';
import { RefreshCw, Info } from 'lucide-react';

function App() {
  const [coins, setCoins] = useState([]);
  const [selectedCoin, setSelectedCoin] = useState('BTC');
  const [marketData, setMarketData] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [showInfo, setShowInfo] = useState(false);

  useEffect(() => {
    async function init() {
      try {
        const c = await getCoins();
        setCoins(c);
        loadData(selectedCoin);
      } catch (e) {
        console.error("Failed to init", e);
      }
    }
    init();
  }, []);

  const loadData = async (coin) => {
    setLoading(true); // Initial load only
    setRefreshData(coin);
  };

  const handleRefresh = () => {
    setRefreshing(true);
    setRefreshData(selectedCoin).finally(() => setRefreshing(false));
  };

  const setRefreshData = async (coin) => {
    // 1. Load Market Data immediately (Fast)
    try {
      const mData = await getMarketData(coin);
      setMarketData(mData);
      setLoading(false); // Creating specific loading state for chart vs prediction would be better, but this unblocks the view

      // 2. Load AI Predictions (Slow)
      // We do this separately so the chart shows up while the AI "thinks"
      const [predData, valData] = await Promise.all([
        getPrediction(coin),
        getValidation(coin).catch(e => null)
      ]);

      setPrediction(predData);
      setValidation(valData);
    } catch (e) {
      console.error("Data Error", e);
      setLoading(false); // Ensure loading stops on error
    }
  }

  const handleCoinChange = (coin) => {
    setSelectedCoin(coin);
    loadData(coin);
  };

  // ... (Derived State Calculation Same as Before)
  const currentPrice = marketData.length > 0 ? marketData[marketData.length - 1].close : 0;
  const prevPrice = marketData.length > 1 ? marketData[marketData.length - 2].close : currentPrice;
  const priceChange = currentPrice - prevPrice;
  const percentChange = (priceChange / prevPrice) * 100;

  const nextDayPred = prediction ? prediction.forecast.mean[0] : 0;
  const forecastTrend = nextDayPred > currentPrice ? 'up' : 'down';
  const forecastDiff = ((nextDayPred - currentPrice) / currentPrice) * 100;

  const upper = prediction ? prediction.forecast.upper[0] : 0;
  const lower = prediction ? prediction.forecast.lower[0] : 0;
  const spread = nextDayPred > 0 ? ((upper - lower) / nextDayPred) * 100 : 0;

  return (
    <div className="min-h-screen bg-[#0e1117] text-gray-200 font-sans pb-20">

      <CoinSelector
        coins={coins}
        selectedCoin={selectedCoin}
        onSelect={handleCoinChange}
      />

      <ProjectInfo isOpen={showInfo} onClose={() => setShowInfo(false)} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8 space-y-8">

        {/* Header Actions */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="flex justify-end gap-3"
        >
          <button
            onClick={() => setShowInfo(true)}
            className="flex items-center gap-2 px-4 py-2 bg-[#1e1e1e] border border-[#333] rounded-lg hover:bg-[#252525] transition-colors text-sm font-medium text-gray-300"
          >
            <Info size={16} className="text-blue-400" />
            About & Disclaimer
          </button>

          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-4 py-2 bg-[#1e1e1e] border border-[#333] rounded-lg hover:bg-[#252525] transition-colors text-sm font-medium text-gray-300"
            disabled={refreshing}
          >
            <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Refreshing..." : "Refresh Data"}
          </button>
        </motion.div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <MetricsCard
            title="Price / 24h"
            value={`$${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
            subValue={`${percentChange > 0 ? '+' : ''}${percentChange.toFixed(2)}%`}
            trend={percentChange >= 0 ? 'up' : 'down'}
            className={percentChange >= 0 ? "border-green-500/20" : "border-red-500/20"}
          />
          <MetricsCard
            title="7-Day Model Forecast"
            value={prediction ? `$${nextDayPred.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : "Loading..."}
            subValue={prediction ? `${forecastDiff > 0 ? '+' : ''}${forecastDiff.toFixed(2)}% from now` : ""}
            trend={forecastTrend}
            tooltip="Average price predicted for tomorrow based on the LSTM model."
            className="border-yellow-500/30 bg-yellow-500/5"
          />
          <MetricsCard
            title="Forecast Uncertainty"
            value={prediction ? `±${(spread / 2).toFixed(2)}%` : "Calculating..."}
            subValue="Volatility Spread"
            tooltip={`The model's 90% confidence interval spans a ${spread.toFixed(2)}% range based on current market volatility.`}
          />
        </div>

        {/* Chart */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.5 }}
          className="bg-[#1e1e1e] border border-[#333] rounded-3xl p-1 shadow-2xl"
        >
          <div className="bg-[#1e1e1e] rounded-[1.4rem] p-6">
            <PriceChart data={marketData} forecast={prediction ? prediction.forecast : null} />
          </div>
        </motion.div>

        {/* Validation Section (New) */}
        {validation && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="bg-[#1e1e1e] border border-[#333] rounded-2xl p-6"
          >
            <h3 className="text-lg font-bold flex items-center gap-2 mb-2">
              🎯 Model Accuracy (Last 30 Days)
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              Comparison of what the model <em>would have predicted</em> vs what actually happened.
            </p>
            <ValidationChart data={validation} />
          </motion.div>
        )}

        {/* Explainability */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="grid grid-cols-1 lg:grid-cols-1 gap-6"
        >
          <ModelExplainer
            trend={forecastTrend}
            analysis={{
              rsi: 55,
              macd: forecastDiff,
              volatility: (currentPrice * 0.02)
            }}
          />
        </motion.div>

      </div>
    </div>
  );
}

export default App;
