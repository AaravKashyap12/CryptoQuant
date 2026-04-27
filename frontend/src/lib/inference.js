import * as tf from '@tensorflow/tfjs';

/**
 * Run edge-side TF.js inference for a coin.
 *
 * The backend model expects input shape (1, lookback, n_features) where
 * n_features = 15 (close, open, high, low, volume, rsi, MACD×3, EMA×3, ATR, vol_ma, sentiment).
 *
 * This function receives pre-processed, scaled feature rows from the caller
 * so it never needs to know about feature engineering internals.
 *
 * @param {string} coin           - e.g. "BTC"
 * @param {number[][]} inputMatrix - shape (lookback, n_features) — scaled, all 15 features
 * @param {string} apiOrigin       - base URL without /api/v1, e.g. "https://api.example.com"
 * @returns {number[] | null}      - raw scaled output array, or null on error
 */
export async function runEdgeInference(coin, inputMatrix, apiOrigin) {
    try {
        // Strip any trailing /api/v1 the caller may accidentally include
        const origin = apiOrigin.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
        const modelUrl = `${origin}/api/v1/model/${coin}/tfjs/model.json`;

        const model = await tf.loadLayersModel(modelUrl);

        // inputMatrix must be shape (lookback, n_features)
        if (!Array.isArray(inputMatrix) || !Array.isArray(inputMatrix[0])) {
            throw new Error(
                `runEdgeInference: inputMatrix must be 2D array (lookback × n_features). ` +
                `Got: ${JSON.stringify(inputMatrix).slice(0, 80)}`
            );
        }

        // Shape: (1, lookback, n_features)
        const inputTensor = tf.tensor3d([inputMatrix]);
        const prediction  = model.predict(inputTensor);
        const output      = Array.from(await prediction.data());

        inputTensor.dispose();
        prediction.dispose();
        model.dispose();

        return output;
    } catch (error) {
        console.error('[EdgeInference] Error:', error);
        return null;
    }
}

/**
 * Build the 15-feature input matrix from raw market data rows.
 * Call this before runEdgeInference — it replicates the Python feature pipeline
 * (without scaling; the model served via TFJS includes the scaler baked in,
 * or you must scale separately if using a plain Keras export).
 *
 * NOTE: If your TFJS export does NOT include the scaler, you need to pass
 * pre-scaled data. This helper produces unscaled features as a reference.
 *
 * @param {object[]} candles - array of {close, open, high, low, volume} objects
 * @param {number}   lookback - number of timesteps (default 60)
 * @param {number}   sentimentScore - latest Fear & Greed score (default 50)
 * @returns {number[][] | null} - shape (lookback, 15), or null if not enough data
 */
export function buildFeatureMatrix(candles, lookback = 60, sentimentScore = 50) {
    if (!candles || candles.length < lookback + 14) {
        console.warn('[EdgeInference] Not enough candles to build feature matrix');
        return null;
    }

    const slice = candles.slice(-lookback - 14);  // extra rows needed for indicator warmup
    const sentiment = Number.isFinite(Number(sentimentScore)) ? Number(sentimentScore) : 50;

    // ── RSI (period 14) ──────────────────────────────────────────────────────
    function rsi(closes, period = 14) {
        const deltas = closes.slice(1).map((value, i) => value - closes[i]);
        const gains = deltas.map(delta => delta > 0 ? delta : 0);
        const losses = deltas.map(delta => delta < 0 ? -delta : 0);
        const result = Array(period).fill(50);

        if (deltas.length < period) {
            return result.slice(0, closes.length - 1);
        }

        let ag = gains.slice(0, period).reduce((total, value) => total + value, 0) / period;
        let al = losses.slice(0, period).reduce((total, value) => total + value, 0) / period;

        for (let i = period; i < deltas.length; i++) {
            ag = ag * (1 - 1 / period) + gains[i] * (1 / period);
            al = al * (1 - 1 / period) + losses[i] * (1 / period);
            result.push(al === 0 ? 100 : 100 - 100 / (1 + ag / al));
        }

        return result;
    }

    // ── EMA ──────────────────────────────────────────────────────────────────
    function ema(closes, period) {
        const k = 2 / (period + 1);
        const result = [closes[0]];
        for (let i = 1; i < closes.length; i++) {
            result.push(closes[i] * k + result[i - 1] * (1 - k));
        }
        return result;
    }

    const closes  = slice.map(c => c.close);
    const highs   = slice.map(c => c.high);
    const lows    = slice.map(c => c.low);
    const volumes = slice.map(c => c.volume);

    const rsiVals   = rsi(closes);
    const ema12     = ema(closes, 12);
    const ema26     = ema(closes, 26);
    const ema7      = ema(closes, 7);
    const ema25     = ema(closes, 25);
    const ema50     = ema(closes, 50);
    const macdLine  = ema12.map((v, i) => v - ema26[i]);
    const macdSig   = ema(macdLine, 9);
    const macdHist  = macdLine.map((v, i) => v - macdSig[i]);

    // ── ATR (period 14) ──────────────────────────────────────────────────────
    const tr = slice.map((c, i) => {
        if (i === 0) return highs[i] - lows[i];
        const prevClose = slice[i - 1].close;
        return Math.max(
            highs[i]  - lows[i],
            Math.abs(highs[i]  - prevClose),
            Math.abs(lows[i]   - prevClose),
        );
    });
    function rollingMean(arr, period) {
        return arr.map((_, i) =>
            i < period - 1
                ? arr.slice(0, i + 1).reduce((a, b) => a + b) / (i + 1)
                : arr.slice(i - period + 1, i + 1).reduce((a, b) => a + b) / period
        );
    }
    const atrVals  = rollingMean(tr, 14);
    const volMa20  = rollingMean(volumes, 20);

    // ── Assemble rows — skip warmup rows to return exactly `lookback` rows ──
    const warmup = slice.length - lookback;
    const matrix = [];
    for (let i = warmup; i < slice.length; i++) {
        const rsiIdx = i - 1;  // rsi() output is 1 shorter than input (diff)
        const rsiValue = Number.isFinite(rsiVals[rsiIdx]) ? rsiVals[rsiIdx] : 50;
        matrix.push([
            closes[i],              // 0  close
            slice[i].high,          // 1  high
            slice[i].low,           // 2  low
            slice[i].open,          // 3  open
            volumes[i],             // 4  volume
            rsiValue,                // 5  rsi
            macdLine[i],            // 6  MACD_12_26_9
            macdHist[i],            // 7  MACDh_12_26_9
            macdSig[i],             // 8  MACDs_12_26_9
            ema7[i],                // 9  ema_7
            ema25[i],               // 10 ema_25
            ema50[i],               // 11 ema_50
            atrVals[i],             // 12 atr
            volMa20[i],             // 13 vol_ma_20
            sentiment,              // 14 sentiment_score
        ]);
    }
    return matrix;
}
