import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
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
