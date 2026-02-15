import axios from 'axios';

// Auto-switch based on environment
const PROD_DEFAULT = 'https://cryptoquant-api.onrender.com';
const DEV_DEFAULT = 'http://localhost:8001';

const rawUrl = import.meta.env.VITE_API_URL || (import.meta.env.MODE === 'development' ? DEV_DEFAULT : PROD_DEFAULT);

// Ensure /api/v1 suffix
const BASE_URL = rawUrl.endsWith('/api/v1') ? rawUrl : `${rawUrl.replace(/\/$/, '')}/api/v1`;

const api = axios.create({
    baseURL: BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

const API_BASE_URL = BASE_URL;

export const getCoins = async () => {
    const response = await api.get('/coins');
    return response.data;
};

export async function getMarketData(coin, limit = 100) {
    try {
        // Add cache buster to force fresh data
        const res = await fetch(`${API_BASE_URL}/market-data/${coin}?limit=${limit}&t=${Date.now()}`);
        if (!res.ok) throw new Error("Failed to fetch market data");
        return await res.json();
    } catch (error) {
        console.error("API Error:", error);
        return [];
    }
}

export const getPrediction = async (coin) => {
    // Post request but no body needed for now as per backend implementation
    const response = await api.post(`/predict/${coin}`);
    return response.data;
};

export const getMetrics = async (coin) => {
    const response = await api.get(`/metrics/${coin}`);
    return response.data;
};

export const getValidation = async (coin) => {
    const response = await api.get(`/validate/${coin}`);
    return response.data;
};

export const trainModel = async (coin) => {
    const response = await api.post(`/train/${coin}`);
    return response.data;
};

export default api;
