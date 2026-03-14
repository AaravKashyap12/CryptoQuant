"""
CryptoQuant local trainer.

Run this script after pulling the latest data to:
  1. Clear stale cached predictions from previous model versions
  2. Train / fine-tune LSTM models for all 5 coins
  3. Upload model artifacts to Supabase S3
  4. Register new versions in the model registry
  5. Pre-compute and store predictions in the cached_predictions table
     so the API serves fast responses immediately after deployment.
"""
import os
import sys

sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()

import colorama
from colorama import Fore, Style
colorama.init()


def clear_stale_cache(registry):
    """
    Wipe cached_predictions table before retraining so the dashboard
    never serves predictions from a model that no longer exists.
    Previously, if run_prediction_batch failed silently, old stale
    predictions kept being served indefinitely.
    """
    session = registry.Session()
    try:
        deleted = session.execute("DELETE FROM cached_predictions")
        session.commit()
        count = deleted.rowcount if hasattr(deleted, "rowcount") else "all"
        print(f"{Fore.YELLOW}  Cleared {count} stale cached prediction(s) from DB{Style.RESET_ALL}")
    except Exception as e:
        session.rollback()
        print(f"{Fore.YELLOW}  [WARN] Could not clear cache: {e}{Style.RESET_ALL}")
    finally:
        session.close()


def check_data_availability():
    """
    Pre-flight check: verify each coin has enough rows before training.
    Warns loudly if a coin will produce an undertrained model.
    BNB in particular often returns <300 rows from fallback exchanges.
    """
    from shared.utils.data_fetcher import fetch_klines
    from shared.ml.training import COINS

    print(f"\n{Fore.CYAN}Pre-flight — checking data availability …{Style.RESET_ALL}")
    all_ok = True
    for coin in COINS:
        df = fetch_klines(f"{coin}USDT", limit=1500)
        if df is None:
            print(f"  {Fore.RED}[FAIL] {coin}: no data returned{Style.RESET_ALL}")
            all_ok = False
            continue
        rows = len(df)
        source = df["source"].iloc[0] if "source" in df.columns else "unknown"
        colour = Fore.GREEN if rows >= 500 else Fore.RED
        warn = "" if rows >= 500 else f"  <-- WARNING: only {rows} rows, model will be undertrained"
        print(f"  {colour}{coin}: {rows} rows from {source}{warn}{Style.RESET_ALL}")
        if rows < 300:
            all_ok = False
    return all_ok


def run_local_training():
    print(f"\n{Fore.CYAN}{Style.BRIGHT}=== CryptoQuant Local Trainer ==={Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Storage : {os.getenv('S3_ENDPOINT_URL', 'Local')}{Style.RESET_ALL}")
    db_url = os.getenv('DB_URL', '')
    print(f"{Fore.YELLOW}Database: {db_url.split('@')[-1] if '@' in db_url else 'Local SQLite'}{Style.RESET_ALL}")
    print("-" * 40)

    from shared.ml.training import train_job_all_coins
    from shared.ml.predict import run_prediction_batch
    from shared.ml.registry import get_model_registry

    registry = get_model_registry()

    # ── Pre-flight ─────────────────────────────────────────────────────────
    data_ok = check_data_availability()
    if not data_ok:
        print(f"\n{Fore.YELLOW}[WARN] Some coins have insufficient data. "
              f"Continuing, but expect poor accuracy for flagged coins.{Style.RESET_ALL}")

    # ── Step 1: Clear stale cache BEFORE training ──────────────────────────
    # This ensures the dashboard shows nothing rather than wrong old values
    # while the new models are being trained and predictions recomputed.
    print(f"\n{Fore.CYAN}Step 1/3 — Clearing stale prediction cache …{Style.RESET_ALL}")
    clear_stale_cache(registry)

    # ── Step 2: Train ──────────────────────────────────────────────────────
    try:
        print(f"\n{Fore.CYAN}Step 2/3 — Training models …{Style.RESET_ALL}")
        results = train_job_all_coins()
        print(f"{Fore.GREEN}Training complete:{Style.RESET_ALL}")
        for coin, version in results.items():
            ok = not str(version).startswith("Error") and version != "skipped (insufficient data)"
            colour = Fore.GREEN if ok else Fore.RED
            print(f"  {colour}{coin}: {version}{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Training failed: {e}{Style.RESET_ALL}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    # ── Step 3: Pre-compute predictions ────────────────────────────────────
    # FIX: Previously this block swallowed ALL exceptions and printed SUCCESS
    # even when prediction batch failed — leaving stale predictions in DB.
    # Now we re-raise on failure and exit with code 1 so CI/CD catches it.
    print(f"\n{Fore.CYAN}Step 3/3 — Pre-computing predictions (n_iter=20) …{Style.RESET_ALL}")
    try:
        pred_results = run_prediction_batch(n_iter=20)
        all_pred_ok = True
        for coin, status in pred_results.items():
            ok = status == "ok"
            colour = Fore.GREEN if ok else Fore.RED
            print(f"  {colour}{coin}: {status}{Style.RESET_ALL}")
            if not ok:
                all_pred_ok = False

        if not all_pred_ok:
            print(f"\n{Fore.YELLOW}[WARN] Some predictions failed — "
                  f"affected coins will run live inference on first request.{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.GREEN}All predictions pre-computed successfully.{Style.RESET_ALL}")

    except Exception as e:
        # FIX: No longer silently swallowed — print full traceback and exit 1
        print(f"\n{Fore.RED}[ERROR] Prediction batch failed: {e}{Style.RESET_ALL}")
        import traceback; traceback.print_exc()
        print(f"\n{Fore.RED}Cached predictions were cleared but not repopulated.")
        print(f"The API will fall back to live inference — run this script again to fix.{Style.RESET_ALL}")
        sys.exit(1)

    print("\n" + "-" * 40)
    print(f"{Fore.GREEN}{Style.BRIGHT}SUCCESS — models trained and predictions pre-computed!{Style.RESET_ALL}")
    
    # NEW: Flush validation/prediction caches so the dashboard updates immediately
    try:
        from shared.ml.cache import cache
        n_val = cache.flush_pattern("validate:")
        n_pred = cache.flush_pattern("pred:")
        print(f"{Fore.CYAN}  Flushed {n_val} validation and {n_pred} prediction cache key(s){Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}  [WARN] Cache flush failed: {e}{Style.RESET_ALL}")

    print(f"{Fore.CYAN}Deploy your API — first request will be served from cache.{Style.RESET_ALL}\n")


if __name__ == "__main__":
    run_local_training()