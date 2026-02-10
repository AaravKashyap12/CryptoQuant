import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8001/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
});

export const getCoins = async () => {
    const response = await api.get('/coins');
    return response.data;
};

export const getMarketData = async (coin) => {
    const response = await api.get(`/market-data/${coin}`);
    return response.data;
};

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

export default api;
