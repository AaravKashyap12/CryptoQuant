import os
import json
import joblib
import tempfile
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from shared.core.config import settings
from shared.ml.storage import get_artifact_store

# --- Database Schema ---
Base = declarative_base()

class ModelVersion(Base):
    __tablename__ = "model_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    coin = Column(String, index=True)
    version = Column(String)
    s3_key_prefix = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    metrics = Column(JSON)
    config = Column(JSON)

# --- Registry Implementation ---
class ModelRegistry:
    def __init__(self):
        self.storage = get_artifact_store()
        
        if settings.USE_POSTGRES:
            self.engine = create_engine(settings.DB_URL)
        else:
            print(f"Using SQLite Registry: {settings.SQLITE_URL}")
            self.engine = create_engine(settings.SQLITE_URL, connect_args={"check_same_thread": False})
            
        Base.metadata.create_all(self.engine) # Auto-create tables
        self.Session = sessionmaker(bind=self.engine)
        
        # Local Cache for loaded models
        self.cache = {} 

    def dispose(self):
        """Releases the database engine resources."""
        if hasattr(self, 'engine'):
            self.engine.dispose()
    def get_latest_version_metadata(self, coin):
        session = self.Session()
        try:
            latest = session.query(ModelVersion).filter_by(coin=coin).order_by(ModelVersion.id.desc()).first()
            if not latest:
                return None
            return {
                "version": latest.version,
                "s3_key_prefix": latest.s3_key_prefix,
                "metrics": latest.metrics,
                "config": latest.config
            }
        finally:
            session.close()

    def get_latest_version(self, coin):
        meta = self.get_latest_version_metadata(coin)
        return meta['version'] if meta else "v0.0.0"

    def _increment_version(self, latest_version):
        if not latest_version:
            return "v1.0.0"
        major, minor, patch = map(int, latest_version[1:].split('.'))
        return f"v{major}.{minor}.{patch+1}"

    def save_model(self, coin, model, scaler, target_scaler, metrics=None):
        """
        Saves model artifacts to Storage (S3/Local) and metadata to DB (PG/SQLite).
        """
        # 1. Determine Version
        latest_meta = self.get_latest_version_metadata(coin)
        latest_ver = latest_meta['version'] if latest_meta else None
        new_version = self._increment_version(latest_ver)
        
        # 2. Upload to Storage
        s3_key_prefix = f"{coin}/{new_version}"
        self.storage.save_model(model, s3_key_prefix)
        self.storage.save_joblib(scaler, s3_key_prefix, "scaler.pkl")
        self.storage.save_joblib(target_scaler, s3_key_prefix, "target_scaler.pkl")
        
        # 3. Save Metadata to DB
        session = self.Session()
        try:
            config = {
                "lookback": model.input_shape[1] if hasattr(model, "input_shape") else 60,
                "features": model.input_shape[2] if hasattr(model, "input_shape") else None
            }
            
            new_record = ModelVersion(
                coin=coin,
                version=new_version,
                s3_key_prefix=s3_key_prefix,
                metrics=metrics or {},
                config=config
            )
            session.add(new_record)
            session.commit()
            print(f"Registered {coin} {new_version} in DB")
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            
        return new_version

    def load_latest_model(self, coin):
        """
        Loads the latest model for a coin.
        Returns: (model, scaler, target_scaler, metadata)
        """
        meta = self.get_latest_version_metadata(coin)
        if not meta:
            return None, None, None, None
            
        version = meta['version']
        cache_key = f"{coin}_{version}"
        
        # Check Memory Cache
        if cache_key in self.cache:
            print(f"Loading {coin} {version} from MEMORY CACHE")
            return self.cache[cache_key]
            
        # Download from Storage to Temp
        s3_prefix = meta['s3_key_prefix']
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                print(f"Downloading {coin} {version} from Storage...")
                
                # Download
                model_path = self.storage.load_model_to_path(s3_prefix, temp_dir)
                scaler = self.storage.load_joblib(s3_prefix, "scaler.pkl", temp_dir)
                target_scaler = self.storage.load_joblib(s3_prefix, "target_scaler.pkl", temp_dir)
                
                # Load Keras Model
                from tensorflow.keras.models import load_model
                model = load_model(model_path)
                
                # Cache results
                result = (model, scaler, target_scaler, meta)
                self.cache[cache_key] = result
                
                return result
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Failed to load {coin} {version}: {e}")
            return None, None, None, None

# Singleton instance for the whole application
_global_registry = None

def get_model_registry() -> ModelRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = ModelRegistry()
    return _global_registry
