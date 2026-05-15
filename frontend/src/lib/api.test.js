import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getCoins,
  clearPublicApiCache,
  fetchJson,
  normalizeBinanceKlines,
  buildBaselinePrediction,
  buildValidationSeries,
} from './api.js';

function makeCandles(count) {
  return Array.from({ length: count }, (_, i) => ({
    open_time: Date.UTC(2026, 0, i + 1),
    open: 100 + i,
    high: 104 + i,
    low: 98 + i,
    close: 101 + i,
    volume: 1000 + i * 10,
  }));
}

test('getCoins returns the frontend-only supported symbols', async () => {
  assert.deepEqual(await getCoins(), ['BTC', 'ETH', 'BNB', 'SOL', 'ADA']);
});

test('normalizeBinanceKlines converts public kline arrays into chart candles', () => {
  const rows = [
    [1710000000000, '100.5', '104.25', '99.75', '102.125', '12345.6'],
  ];

  assert.deepEqual(normalizeBinanceKlines(rows), [{
    open_time: 1710000000000,
    open: 100.5,
    high: 104.25,
    low: 99.75,
    close: 102.125,
    volume: 12345.6,
    rsi: 50,
  }]);
});

test('fetchJson reuses cached responses for the same URL under 60 seconds', async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    return {
      ok: true,
      json: async () => ({ calls }),
    };
  };

  try {
    clearPublicApiCache();
    const url = 'https://example.test/public';
    const first = await fetchJson(url, { now: () => 1000 });
    const second = await fetchJson(url, { now: () => 30_000 });

    assert.deepEqual(first, { calls: 1 });
    assert.deepEqual(second, { calls: 1 });
    assert.equal(calls, 1);
  } finally {
    clearPublicApiCache();
    globalThis.fetch = originalFetch;
  }
});

test('fetchJson refreshes cached responses after 60 seconds', async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    return {
      ok: true,
      json: async () => ({ calls }),
    };
  };

  try {
    clearPublicApiCache();
    const url = 'https://example.test/public';
    const first = await fetchJson(url, { now: () => 1000 });
    const second = await fetchJson(url, { now: () => 62_000 });

    assert.deepEqual(first, { calls: 1 });
    assert.deepEqual(second, { calls: 2 });
    assert.equal(calls, 2);
  } finally {
    clearPublicApiCache();
    globalThis.fetch = originalFetch;
  }
});

test('buildBaselinePrediction returns forecast bands from recent volatility', () => {
  const prediction = buildBaselinePrediction('BTC', makeCandles(80));

  assert.equal(prediction.coin, 'BTC');
  assert.equal(prediction.forecast.mean.length, 1);
  assert.equal(prediction.forecast.upper.length, 1);
  assert.equal(prediction.forecast.lower.length, 1);
  assert.ok(prediction.forecast.upper[0] > prediction.forecast.mean[0]);
  assert.ok(prediction.forecast.lower[0] < prediction.forecast.mean[0]);
  assert.equal(prediction.metadata.serving_mode, 'browser statistical baseline');
});

test('buildValidationSeries creates rolling actual versus predicted points', () => {
  const series = buildValidationSeries(makeCandles(80), 30);

  assert.equal(series.length, 30);
  assert.deepEqual(Object.keys(series[0]).sort(), ['actual', 'date', 'predicted'].sort());
  assert.ok(series.every(point => Number.isFinite(point.actual)));
  assert.ok(series.every(point => Number.isFinite(point.predicted)));
});
