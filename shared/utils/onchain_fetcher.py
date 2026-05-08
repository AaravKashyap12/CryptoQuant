from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx

from shared.core.config import settings


BINANCE_FUTURES_BASE_URL = "https://fapi.binance.com"
GLASSNODE_BASE_URL = "https://api.glassnode.com/v1/metrics"
SUPPORTED_COINS = {"BTC", "ETH", "BNB", "SOL", "ADA"}
GLASSNODE_SUPPORTED_ASSETS = {"BTC", "ETH"}


GLASSNODE_METRICS = {
    "exchange_netflow": {
        "label": "EXCHANGE NETFLOW",
        "path": "transactions/transfers_volume_exchanges_net",
        "unit": "USD",
        "currency": "USD",
        "description": "Positive means exchange inflow; negative means exchange outflow.",
    },
    "active_addresses_7d": {
        "label": "ACTIVE ADDRESSES",
        "path": "addresses/active_count",
        "unit": "addresses",
        "description": "Network demand proxy.",
    },
    "sopr": {
        "label": "SOPR",
        "path": "indicators/sopr",
        "unit": "ratio",
        "description": "Spent output profit ratio.",
    },
    "mvrv_z_score": {
        "label": "MVRV Z-SCORE",
        "path": "market/mvrv_z_score",
        "unit": "z",
        "description": "Market value versus realized value.",
    },
    "miner_outflows": {
        "label": "MINER TO EXCHANGES",
        "path": "transactions/transfers_volume_miners_to_exchanges_all",
        "unit": "native",
        "description": "BTC miner sell-pressure proxy.",
        "assets": {"BTC"},
    },
}


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _series_change_pct(values: list[float], periods_back: int = 7) -> float | None:
    if len(values) <= periods_back:
        return None
    latest = values[-1]
    previous = values[-periods_back - 1]
    if previous == 0:
        return None
    return ((latest - previous) / abs(previous)) * 100


def _latest_numeric_value(points: list[dict[str, Any]]) -> tuple[float | None, int | None]:
    for point in reversed(points or []):
        raw = point.get("v")
        if isinstance(raw, dict):
            numeric_values = [v for v in raw.values() if isinstance(v, (int, float))]
            raw = sum(numeric_values) if numeric_values else None
        value = _to_float(raw)
        if value is not None:
            return value, int(point.get("t")) if point.get("t") else None
    return None, None


def _change_pct(points: list[dict[str, Any]], days: int = 7) -> float | None:
    values = []
    for point in points or []:
        value = _to_float(point.get("v"))
        if value is not None:
            values.append(value)
    return _series_change_pct(values, days)


def _fetch_glassnode_metric(client: httpx.Client, asset: str, spec: dict[str, Any]) -> list[dict[str, Any]]:
    since = int(time.time()) - 90 * 24 * 60 * 60
    params = {
        "a": asset,
        "api_key": settings.GLASSNODE_API_KEY,
        "i": "24h",
        "s": since,
        "f": "json",
    }
    if spec.get("currency"):
        params["c"] = spec["currency"]

    response = client.get(f"{GLASSNODE_BASE_URL}/{spec['path']}", params=params)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def _fetch_binance_json(client: httpx.Client, path: str, params: dict[str, Any]) -> Any:
    response = client.get(f"{BINANCE_FUTURES_BASE_URL}{path}", params=params)
    response.raise_for_status()
    return response.json()


def _latest_from_list(items: Any, key: str) -> float | None:
    if not isinstance(items, list) or not items:
        return None
    return _to_float(items[-1].get(key))


def _values_from_list(items: Any, key: str) -> list[float]:
    if not isinstance(items, list):
        return []
    values = []
    for item in items:
        value = _to_float(item.get(key))
        if value is not None:
            values.append(value)
    return values


def _fetch_free_market_signals(coin: str) -> dict[str, Any]:
    if coin not in SUPPORTED_COINS:
        return {
            "coin": coin,
            "status": "unsupported",
            "provider": "binance-public",
            "signals": {},
            "message": f"Free signal support is configured for {', '.join(sorted(SUPPORTED_COINS))}.",
        }

    symbol = f"{coin}USDT"
    signals: dict[str, Any] = {}
    errors: dict[str, str] = {}

    with httpx.Client(timeout=15.0) as client:
        try:
            premium = _fetch_binance_json(client, "/fapi/v1/premiumIndex", {"symbol": symbol})
            funding = _to_float(premium.get("lastFundingRate"))
            mark_price = _to_float(premium.get("markPrice"))
            if funding is not None:
                signals["funding_rate"] = {
                    "label": "FUNDING RATE",
                    "value": funding * 100,
                    "unit": "percent",
                    "description": "Positive means longs pay shorts.",
                }
            if mark_price is not None:
                signals["mark_price"] = {
                    "label": "MARK PRICE",
                    "value": mark_price,
                    "unit": "USD",
                    "description": "Binance futures mark price.",
                }
        except Exception as exc:
            errors["premium_index"] = str(exc)

        try:
            current_oi = _fetch_binance_json(client, "/fapi/v1/openInterest", {"symbol": symbol})
            open_interest = _to_float(current_oi.get("openInterest"))
            if open_interest is not None:
                signals["open_interest"] = {
                    "label": "OPEN INTEREST",
                    "value": open_interest,
                    "unit": "native",
                    "description": "Total open futures contracts.",
                }
        except Exception as exc:
            errors["open_interest"] = str(exc)

        try:
            oi_hist = _fetch_binance_json(
                client,
                "/futures/data/openInterestHist",
                {"symbol": symbol, "period": "1d", "limit": 30},
            )
            oi_values = _values_from_list(oi_hist, "sumOpenInterestValue")
            latest_oi_value = oi_values[-1] if oi_values else None
            if latest_oi_value is not None:
                signals["open_interest_usd"] = {
                    "label": "OI VALUE",
                    "value": latest_oi_value,
                    "unit": "USD",
                    "change_7d_pct": _series_change_pct(oi_values),
                    "description": "Notional futures exposure.",
                }
        except Exception as exc:
            errors["open_interest_history"] = str(exc)

        try:
            ratio = _fetch_binance_json(
                client,
                "/futures/data/globalLongShortAccountRatio",
                {"symbol": symbol, "period": "1d", "limit": 30},
            )
            latest_ratio = _latest_from_list(ratio, "longShortRatio")
            ratio_values = _values_from_list(ratio, "longShortRatio")
            if latest_ratio is not None:
                signals["long_short_ratio"] = {
                    "label": "LONG / SHORT",
                    "value": latest_ratio,
                    "unit": "ratio",
                    "change_7d_pct": _series_change_pct(ratio_values),
                    "description": "Global account long/short ratio.",
                }
        except Exception as exc:
            errors["long_short_ratio"] = str(exc)

        try:
            taker = _fetch_binance_json(
                client,
                "/futures/data/takerlongshortRatio",
                {"symbol": symbol, "period": "1d", "limit": 30},
            )
            latest_taker = _latest_from_list(taker, "buySellRatio")
            taker_values = _values_from_list(taker, "buySellRatio")
            if latest_taker is not None:
                signals["taker_buy_sell_ratio"] = {
                    "label": "TAKER BUY/SELL",
                    "value": latest_taker,
                    "unit": "ratio",
                    "change_7d_pct": _series_change_pct(taker_values),
                    "description": "Aggressive buy flow versus sell flow.",
                }
        except Exception as exc:
            errors["taker_buy_sell_ratio"] = str(exc)

    status = "live" if signals else "error"
    return {
        "coin": coin,
        "status": status,
        "provider": "binance-public",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
        "errors": errors,
        "message": "Free public derivatives data. Useful ML signal, but not true wallet-level on-chain data.",
    }


def _fetch_glassnode_signals(coin: str) -> dict[str, Any]:
    if coin not in GLASSNODE_SUPPORTED_ASSETS:
        return {
            "coin": coin,
            "status": "unsupported",
            "provider": "glassnode",
            "signals": {},
            "message": f"Glassnode support is staged for BTC and ETH first; {coin} is not enabled.",
        }

    if not settings.GLASSNODE_API_KEY:
        return {
            "coin": coin,
            "status": "not_configured",
            "provider": "glassnode",
            "signals": {},
            "message": "Set GLASSNODE_API_KEY to enable premium on-chain metrics.",
        }

    signals: dict[str, Any] = {}
    errors: dict[str, str] = {}
    latest_ts: int | None = None

    with httpx.Client(timeout=15.0) as client:
        for key, spec in GLASSNODE_METRICS.items():
            allowed_assets = spec.get("assets")
            if allowed_assets and coin not in allowed_assets:
                continue
            try:
                points = _fetch_glassnode_metric(client, coin, spec)
                value, ts = _latest_numeric_value(points)
                if value is None:
                    errors[key] = "No numeric value returned"
                    continue
                latest_ts = max(latest_ts or ts or 0, ts or 0) or latest_ts
                signals[key] = {
                    "label": spec["label"],
                    "value": value,
                    "unit": spec["unit"],
                    "change_7d_pct": _change_pct(points),
                    "description": spec["description"],
                }
            except httpx.HTTPStatusError as exc:
                errors[key] = f"HTTP {exc.response.status_code}"
            except Exception as exc:
                errors[key] = str(exc)

    status = "live" if signals else "error"
    updated_at = (
        datetime.fromtimestamp(latest_ts, tz=timezone.utc).isoformat()
        if latest_ts
        else datetime.now(timezone.utc).isoformat()
    )

    return {
        "coin": coin,
        "status": status,
        "provider": "glassnode",
        "updated_at": updated_at,
        "signals": signals,
        "errors": errors,
    }


def fetch_onchain_signals(coin: str) -> dict[str, Any]:
    coin = coin.upper()
    provider = settings.ONCHAIN_PROVIDER
    if provider in {"free", "binance", "binance-public"}:
        return _fetch_free_market_signals(coin)
    if provider == "glassnode":
        return _fetch_glassnode_signals(coin)
    return {
        "coin": coin,
        "status": "not_configured",
        "provider": provider,
        "signals": {},
        "message": "Unsupported ONCHAIN_PROVIDER. Use free or glassnode.",
    }
