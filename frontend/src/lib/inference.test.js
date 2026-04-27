import assert from 'node:assert/strict';
import test from 'node:test';

import { buildFeatureMatrix } from './inference.js';

function makeCandles(count) {
    return Array.from({ length: count }, (_, i) => {
        const close = 100 + i * 1.7 + Math.sin(i / 2) * 4;
        return {
            close,
            high: close + 2 + (i % 3) * 0.25,
            low: close - 2 - (i % 2) * 0.2,
            open: close - 0.8 + Math.cos(i / 3),
            volume: 1000 + i * 13,
        };
    });
}

function ema(values, period) {
    const k = 2 / (period + 1);
    const result = [values[0]];
    for (let i = 1; i < values.length; i += 1) {
        result.push(values[i] * k + result[i - 1] * (1 - k));
    }
    return result;
}

function seededWilderRsi(values, period = 14) {
    const deltas = values.slice(1).map((value, i) => value - values[i]);
    const gains = deltas.map(delta => (delta > 0 ? delta : 0));
    const losses = deltas.map(delta => (delta < 0 ? -delta : 0));
    let avgGain = gains.slice(0, period).reduce((total, value) => total + value, 0) / period;
    let avgLoss = losses.slice(0, period).reduce((total, value) => total + value, 0) / period;
    const result = Array(period).fill(50);

    for (let i = period; i < deltas.length; i += 1) {
        avgGain = avgGain * (1 - 1 / period) + gains[i] * (1 / period);
        avgLoss = avgLoss * (1 - 1 / period) + losses[i] * (1 / period);
        result.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
    }

    return result;
}

test('buildFeatureMatrix passes sentiment into feature index 14', () => {
    const candles = makeCandles(80);
    const matrix = buildFeatureMatrix(candles, 10, 73);

    assert.equal(matrix[0][14], 73);
});

function oldSimpleMovingAverageRsi(values, period = 14) {
    const deltas = values.slice(1).map((value, i) => value - values[i]);
    const gains = deltas.map(delta => (delta > 0 ? delta : 0));
    const losses = deltas.map(delta => (delta < 0 ? -delta : 0));
    return deltas.map((_, i) => {
        if (i < period) return 50;
        const avgGain = gains.slice(i - period + 1, i + 1).reduce((total, value) => total + value, 0) / period;
        const avgLoss = losses.slice(i - period + 1, i + 1).reduce((total, value) => total + value, 0) / period;
        return avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
    });
}

test('buildFeatureMatrix RSI does not use simple rolling averages', () => {
    const candles = makeCandles(80);
    const lookback = 10;
    const matrix = buildFeatureMatrix(candles, lookback);

    const slice = candles.slice(-lookback - 14);
    const closes = slice.map(candle => candle.close);
    const sourceIndex = slice.length - 2;
    const rollingRsi = oldSimpleMovingAverageRsi(closes)[sourceIndex];

    assert.notEqual(matrix[matrix.length - 1][5], rollingRsi);
});

test('buildFeatureMatrix RSI uses seeded Wilder smoothing', () => {
    const candles = makeCandles(80);
    const lookback = 10;
    const matrix = buildFeatureMatrix(candles, lookback);

    const slice = candles.slice(-lookback - 14);
    const closes = slice.map(candle => candle.close);
    const sourceIndex = slice.length - lookback - 1;
    const expectedRsi = seededWilderRsi(closes)[sourceIndex];

    assert.ok(Math.abs(matrix[0][5] - expectedRsi) < 1e-9);
});

function pandasStyleEwmRsi(values, period = 14) {
    const gains = [0];
    const losses = [0];
    for (let i = 1; i < values.length; i += 1) {
        const delta = values[i] - values[i - 1];
        gains.push(delta > 0 ? delta : 0);
        losses.push(delta < 0 ? -delta : 0);
    }

    const alpha = 1 / period;
    const avgGains = [gains[0]];
    const avgLosses = [losses[0]];
    for (let i = 1; i < values.length; i += 1) {
        avgGains.push(gains[i] * alpha + avgGains[i - 1] * (1 - alpha));
        avgLosses.push(losses[i] * alpha + avgLosses[i - 1] * (1 - alpha));
    }

    return avgGains.map((avgGain, i) => {
        const avgLoss = avgLosses[i];
        if (avgLoss === 0 && avgGain === 0) return Number.NaN;
        if (avgLoss === 0) return 100;
        return 100 - 100 / (1 + avgGain / avgLoss);
    });
}

test('buildFeatureMatrix uses ema_50 at feature index 11', () => {
    const candles = makeCandles(80);
    const lookback = 10;
    const matrix = buildFeatureMatrix(candles, lookback);

    assert.equal(matrix.length, lookback);

    const slice = candles.slice(-lookback - 14);
    const closes = slice.map(candle => candle.close);
    const sourceIndex = slice.length - lookback;
    const expectedEma50 = ema(closes, 50)[sourceIndex];

    assert.ok(Math.abs(matrix[0][11] - expectedEma50) < 1e-9);
});

test('buildFeatureMatrix RSI no longer uses pandas zero-seeded ewm smoothing', () => {
    const candles = makeCandles(80);
    const lookback = 10;
    const matrix = buildFeatureMatrix(candles, lookback);

    const slice = candles.slice(-lookback - 14);
    const closes = slice.map(candle => candle.close);
    const sourceIndex = slice.length - lookback;
    const pandasRsi = pandasStyleEwmRsi(closes)[sourceIndex];

    assert.notEqual(matrix[0][5], pandasRsi);
});
