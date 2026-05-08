import { useState, useEffect } from 'react';

/**
 * Hook for live price updates via Binance WebSocket.
 * Even though the project uses CCXT/Kraken for history, 
 * Binance WS is the most reliable for free real-time data in frontend.
 */
export function useLivePrice(symbol) {
    const [ticker, setTicker] = useState({ symbol: null, price: null, change24h: null });

    useEffect(() => {
        if (!symbol) return;
        let active = true;

        // Binance WS symbol: btcusdt (lowercase)
        const wsSymbol = symbol.toLowerCase().replace('/', '');
        const ws = new WebSocket(`wss://stream.binance.com:9443/ws/${wsSymbol}@ticker`);

        ws.onmessage = (event) => {
            if (!active) return;
            try {
                const data = JSON.parse(event.data);
                // c is current price, p is price change
                setTicker({
                    symbol,
                    price: parseFloat(data.c),
                    change24h: parseFloat(data.P),
                });
            } catch (e) {
                console.error("WS Parse Error", e);
            }
        };

        ws.onerror = (err) => {
            if (active) console.error("WS Error:", err);
        };

        return () => {
            active = false;
            if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                ws.close();
            }
        };
    }, [symbol]);

    const isCurrentSymbol = ticker.symbol === symbol;
    return {
        price: isCurrentSymbol ? ticker.price : null,
        change24h: isCurrentSymbol ? ticker.change24h : null,
    };
}
