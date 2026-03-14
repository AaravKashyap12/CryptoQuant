import os
import joblib
import tempfile
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from shared.core.config import settings
from shared.ml.storage import get_artifact_store


# SQLAlchemy 2.x-compatible base
class _Base(DeclarativeBase):
    pass


class ModelVersion(_Base):
    __tablename__ = "model_versions"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    coin          = Column(String, index=True)
    version       = Column(String)
    s3_key_prefix = Column(String)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    metrics       = Column(JSON)
    config        = Column(JSON)


class CachedPrediction(_Base):
    """Stores the most-recent precomputed forecast for each coin."""
    __tablename__ = "cached_predictions"
    coin         = Column(String, primary_key=True)
    computed_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    forecast     = Column(JSON)
    metadata_    = Column("metadata", JSON)


class ModelRegistry:
    def __init__(self):
        self.storage = get_artifact_store()

        if settings.USE_POSTGRES:
            self.engine = create_engine(
                settings.DB_URL,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )
        else:
            print(f"Using SQLite registry: {settings.SQLITE_URL}")
            self.engine = create_engine(
                settings.SQLITE_URL,
                connect_args={"check_same_thread": False},
            )

        _Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        # In-memory model cache — holds all 5 coins simultaneously (LRU, max=5)
        self._model_cache: dict = {}
        self._meta_cache:  dict = {}   # coin → (timestamp_float, meta_dict)

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------
    def get_latest_version_metadata(self, coin: str):
        import time
        if coin in self._meta_cache:
            ts, meta = self._meta_cache[coin]
            if time.time() - ts < 60:
                return meta

        session = self.Session()
        try:
            latest = (
                session.query(ModelVersion)
                .filter_by(coin=coin)
                .order_by(ModelVersion.id.desc())
                .first()
            )
            if not latest:
                return None
            meta = {
                "version":       latest.version,
                "s3_key_prefix": latest.s3_key_prefix,
                "metrics":       latest.metrics,
                "config":        latest.config,
            }
            self._meta_cache[coin] = (time.time(), meta)
            return meta
        finally:
            session.close()

    def get_latest_version(self, coin: str) -> str:
        meta = self.get_latest_version_metadata(coin)
        return meta["version"] if meta else "v0.0.0"

    def _increment_version(self, latest_version: str) -> str:
        if not latest_version or latest_version == "v0.0.0":
            return "v1.0.0"
        major, minor, patch = map(int, latest_version[1:].split("."))
        return f"v{major}.{minor}.{patch + 1}"

    # ------------------------------------------------------------------
    # Save model
    # ------------------------------------------------------------------
    def save_model(self, coin, model, scaler, target_scaler, metrics=None):
        latest_meta = self.get_latest_version_metadata(coin)
        latest_ver  = latest_meta["version"] if latest_meta else None
        new_version = self._increment_version(latest_ver)

        s3_key_prefix = f"{coin}/{new_version}"
        self.storage.save_model(model, s3_key_prefix)
        self.storage.save_tfjs_model(model, s3_key_prefix)
        self.storage.save_joblib(scaler,        s3_key_prefix, "scaler.pkl")
        self.storage.save_joblib(target_scaler, s3_key_prefix, "target_scaler.pkl")

        session = self.Session()
        try:
            config = {
                "lookback": model.input_shape[1] if hasattr(model, "input_shape") else 60,
                "features": model.input_shape[2] if hasattr(model, "input_shape") else None,
            }
            session.add(ModelVersion(
                coin=coin,
                version=new_version,
                s3_key_prefix=s3_key_prefix,
                metrics=metrics or {},
                config=config,
            ))
            session.commit()
            print(f"Registered {coin} {new_version} in DB")
            self._meta_cache.pop(coin, None)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

        return new_version

    # ------------------------------------------------------------------
    # Load model — fixed cache (all 5 coins, no K.clear_session)
    # ------------------------------------------------------------------
    def load_latest_model(self, coin: str):
        """
        Returns (model, scaler, target_scaler, metadata).
        Holds up to MAX_COINS models in memory — LRU eviction, no K.clear_session().
        """
        MAX_COINS = 5

        meta = self.get_latest_version_metadata(coin)
        if not meta:
            return None, None, None, None

        version   = meta["version"]
        cache_key = f"{coin}_{version}"

        if cache_key in self._model_cache:
            print(f"[Cache HIT] {coin} {version}")
            return self._model_cache[cache_key]

        if len(self._model_cache) >= MAX_COINS:
            evict_key = next(iter(self._model_cache))
            del self._model_cache[evict_key]
            print(f"[Cache EVICT] {evict_key} (LRU)")
            # ✅ No K.clear_session() — other models stay valid

        try:
            with tempfile.TemporaryDirectory() as tmp:
                print(f"[Cache MISS] Downloading {coin} {version} …")
                model_path    = self.storage.load_model_to_path(meta["s3_key_prefix"], tmp)
                scaler        = self.storage.load_joblib(meta["s3_key_prefix"], "scaler.pkl",        tmp)
                target_scaler = self.storage.load_joblib(meta["s3_key_prefix"], "target_scaler.pkl", tmp)

                from tensorflow.keras.models import load_model
                model = load_model(model_path)

                result = (model, scaler, target_scaler, meta)
                self._model_cache[cache_key] = result
                return result

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Failed to load {coin} {version}: {e}")
            return None, None, None, None

    # ------------------------------------------------------------------
    # Pre-warm — load all models before first request
    # ------------------------------------------------------------------
    def prewarm_all(self, coins=None):
        from shared.ml.training import COINS as ALL_COINS
        for coin in (coins or ALL_COINS):
            try:
                model, _, _, meta = self.load_latest_model(coin)
                status = f"{meta['version']} OK" if model else "no model (skipped)"
                print(f"[Prewarm] {coin}: {status}")
            except Exception as e:
                print(f"[Prewarm] {coin} failed: {e}")

    # ------------------------------------------------------------------
    # Cached prediction store
    # ------------------------------------------------------------------
    def get_cached_prediction(self, coin: str):
        session = self.Session()
        try:
            row = session.query(CachedPrediction).filter_by(coin=coin).first()
            if row is None:
                return None
            age_hours = (
                datetime.now(timezone.utc) - row.computed_at.replace(tzinfo=timezone.utc)
            ).total_seconds() / 3600
            if age_hours > settings.PREDICTION_STALE_HOURS:
                return None
            return {
                "forecast":    row.forecast,
                "metadata":    row.metadata_,
                "computed_at": row.computed_at.isoformat(),
                "from_cache":  True,
            }
        finally:
            session.close()

    def save_cached_prediction(self, coin: str, forecast: dict, metadata: dict):
        session = self.Session()
        try:
            row = session.query(CachedPrediction).filter_by(coin=coin).first()
            now = datetime.now(timezone.utc)
            if row:
                row.forecast   = forecast
                row.metadata_  = metadata
                row.computed_at = now
            else:
                session.add(CachedPrediction(
                    coin=coin,
                    forecast=forecast,
                    metadata_=metadata,
                    computed_at=now,
                ))
            session.commit()
            print(f"[PredictionStore] Saved {coin}")
        except Exception as e:
            session.rollback()
            print(f"[PredictionStore] Save failed for {coin}: {e}")
        finally:
            session.close()

    def dispose(self):
        if hasattr(self, "engine"):
            self.engine.dispose()


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------
_global_registry = None

def get_model_registry() -> ModelRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = ModelRegistry()
    return _global_registry
