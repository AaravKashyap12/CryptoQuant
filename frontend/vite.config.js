import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        // Proxy /api requests to the local FastAPI server during development.
        // This avoids CORS issues and means you don't need VITE_API_URL set locally.
        proxy: {
            '/api': {
                target: 'http://127.0.0.1:8002',
                changeOrigin: true,
                rewrite: path => path,
            },
        },
    },
    build: {
        // Split vendor chunks to improve caching
        rollupOptions: {
            output: {
                manualChunks: {
                    vendor:   ['react', 'react-dom'],
                    charts:   ['recharts'],
                    motion:   ['framer-motion'],
                    tfjs:     ['@tensorflow/tfjs'],
                },
            },
        },
    },
});
