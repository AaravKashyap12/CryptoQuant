import { useState, useEffect } from 'react';

/**
 * Hook for live price updates via Binance WebSocket.
 * Even though the project uses CCXT/Kraken for history, 
 * Binance WS is the most reliable for free real-time data in frontend.
 */
export function useLivePrice(symbol) {
    const [price, setPrice] = useState(null);
    const [change24h, setChange24h] = useState(null);

    useEffect(() => {
        if (!symbol) return;
        let active = true;

        // Reset state so old price doesn't show for a split second
        setPrice(null);
        setChange24h(null);

        // Binance WS symbol: btcusdt (lowercase)
        const wsSymbol = symbol.toLowerCase().replace('/', '');
        const ws = new WebSocket(`wss://stream.binance.com:9443/ws/${wsSymbol}@ticker`);

        ws.onmessage = (event) => {
            if (!active) return;
            try {
                const data = JSON.parse(event.data);
                // c is current price, p is price change
                setPrice(parseFloat(data.c));
                setChange24h(parseFloat(data.P));
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

    return { price, change24h };
}
