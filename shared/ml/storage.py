import boto3
import os
import joblib
import tempfile
import shutil
from abc import ABC, abstractmethod
from shared.core.config import settings

class ArtifactStore(ABC):
    @abstractmethod
    def save_model(self, model, key_prefix: str): pass
    @abstractmethod
    def save_joblib(self, obj, key_prefix: str, filename: str): pass
    @abstractmethod
    def load_model_to_path(self, key_prefix: str, download_dir: str): pass
    @abstractmethod
    def load_joblib(self, key_prefix: str, filename: str, download_dir: str): pass

class S3ArtifactStore(ArtifactStore):
    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )
        self.bucket = settings.S3_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except:
            pass

    def save_file(self, local_path: str, s3_key: str):
        self.s3.upload_file(local_path, self.bucket, s3_key)

    def load_file(self, s3_key: str, local_path: str):
        self.s3.download_file(self.bucket, s3_key, local_path)
            
    def save_model(self, model, key_prefix: str):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = os.path.join(temp_dir, "model.keras")
            model.save(model_path)
            self.save_file(model_path, f"{key_prefix}/model.keras")

    def save_joblib(self, obj, key_prefix: str, filename: str):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, filename)
            joblib.dump(obj, path)
            self.save_file(path, f"{key_prefix}/{filename}")

    def load_model_to_path(self, key_prefix: str, download_dir: str):
        local_path = os.path.join(download_dir, "model.keras")
        self.load_file(f"{key_prefix}/model.keras", local_path)
        return local_path

    def load_joblib(self, key_prefix: str, filename: str, download_dir: str):
        local_path = os.path.join(download_dir, filename)
        self.load_file(f"{key_prefix}/{filename}", local_path)
        return joblib.load(local_path)

class LocalArtifactStore(ArtifactStore):
    def __init__(self):
        self.base_dir = settings.LOCAL_STORAGE_DIR
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
    def _get_path(self, key_prefix, filename):
        # key_prefix likes "BTC/v1.0.1"
        # path -> data/models_storage/BTC/v1.0.1/filename
        full_dir = os.path.join(self.base_dir, key_prefix)
        if not os.path.exists(full_dir):
            os.makedirs(full_dir)
        return os.path.join(full_dir, filename)

    def save_model(self, model, key_prefix: str):
        path = self._get_path(key_prefix, "model.keras")
        model.save(path)
        print(f"Saved local model to {path}")

    def save_joblib(self, obj, key_prefix: str, filename: str):
        path = self._get_path(key_prefix, filename)
        joblib.dump(obj, path)

    def load_model_to_path(self, key_prefix: str, download_dir: str):
        # We copy from storage to download_dir to mimic S3 behavior (safe temp usage)
        # Or we could return the direct path?
        # Keras load_model might modify it? No.
        # But consistent behavior with S3 is better.
        src = self._get_path(key_prefix, "model.keras")
        dst = os.path.join(download_dir, "model.keras")
        shutil.copy2(src, dst)
        return dst

    def load_joblib(self, key_prefix: str, filename: str, download_dir: str):
        src = self._get_path(key_prefix, filename)
        dst = os.path.join(download_dir, filename)
        shutil.copy2(src, dst)
        return joblib.load(dst)

def get_artifact_store():
    if settings.USE_S3:
        return S3ArtifactStore()
    return LocalArtifactStore()
