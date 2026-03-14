import boto3
import os
import joblib
import tempfile
import shutil
from abc import ABC, abstractmethod
from shared.core.config import settings


class ArtifactStore(ABC):
    """Abstract interface for model artifact persistence."""

    @abstractmethod
    def save_model(self, model, key_prefix: str): ...

    @abstractmethod
    def save_joblib(self, obj, key_prefix: str, filename: str): ...

    @abstractmethod
    def load_model_to_path(self, key_prefix: str, download_dir: str) -> str: ...

    @abstractmethod
    def load_joblib(self, key_prefix: str, filename: str, download_dir: str): ...

    @abstractmethod
    def save_tfjs_model(self, model, key_prefix: str): ...

    @abstractmethod
    def save_file(self, local_path: str, remote_key: str): ...

    @abstractmethod
    def load_file(self, remote_key: str, local_path: str): ...


# ─────────────────────────────────────────────────────────────────────────────
# S3 / Supabase Storage
# ─────────────────────────────────────────────────────────────────────────────
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
        except Exception:
            pass  # bucket exists or permissions don't allow head_bucket — proceed

    def save_file(self, local_path: str, remote_key: str):
        self.s3.upload_file(local_path, self.bucket, remote_key)

    def load_file(self, remote_key: str, local_path: str):
        self.s3.download_file(self.bucket, remote_key, local_path)

    def save_model(self, model, key_prefix: str):
        with tempfile.TemporaryDirectory() as tmp:
            model_path = os.path.join(tmp, "model.keras")
            model.save(model_path)
            self.save_file(model_path, f"{key_prefix}/model.keras")

    def save_joblib(self, obj, key_prefix: str, filename: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, filename)
            joblib.dump(obj, path)
            self.save_file(path, f"{key_prefix}/{filename}")

    def load_model_to_path(self, key_prefix: str, download_dir: str) -> str:
        local_path = os.path.join(download_dir, "model.keras")
        self.load_file(f"{key_prefix}/model.keras", local_path)
        return local_path

    def load_joblib(self, key_prefix: str, filename: str, download_dir: str):
        local_path = os.path.join(download_dir, filename)
        self.load_file(f"{key_prefix}/{filename}", local_path)
        return joblib.load(local_path)

    def save_tfjs_model(self, model, key_prefix: str):
        try:
            import tensorflowjs as tfjs
            with tempfile.TemporaryDirectory() as tmp:
                tfjs_dir = os.path.join(tmp, "tfjs")
                os.makedirs(tfjs_dir)
                tfjs.converters.save_keras_model(model, tfjs_dir)
                for fname in os.listdir(tfjs_dir):
                    self.save_file(
                        os.path.join(tfjs_dir, fname),
                        f"{key_prefix}/tfjs/{fname}",
                    )
        except ImportError:
            print("[WARN] tensorflowjs not installed — skipping TFJS export.")
        except Exception as e:
            print(f"[ERROR] TFJS S3 export failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Local filesystem (dev / CI)
# ─────────────────────────────────────────────────────────────────────────────
class LocalArtifactStore(ArtifactStore):
    def __init__(self):
        self.base_dir = settings.LOCAL_STORAGE_DIR
        os.makedirs(self.base_dir, exist_ok=True)

    def _dir(self, key_prefix: str) -> str:
        d = os.path.join(self.base_dir, key_prefix)
        os.makedirs(d, exist_ok=True)
        return d

    def save_file(self, local_path: str, remote_key: str):
        dst = os.path.join(self.base_dir, remote_key)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(local_path, dst)

    def load_file(self, remote_key: str, local_path: str):
        src = os.path.join(self.base_dir, remote_key)
        shutil.copy2(src, local_path)

    def save_model(self, model, key_prefix: str):
        path = os.path.join(self._dir(key_prefix), "model.keras")
        model.save(path)
        print(f"[LocalStore] saved model -> {path}")

    def save_joblib(self, obj, key_prefix: str, filename: str):
        joblib.dump(obj, os.path.join(self._dir(key_prefix), filename))

    def load_model_to_path(self, key_prefix: str, download_dir: str) -> str:
        src = os.path.join(self.base_dir, key_prefix, "model.keras")
        dst = os.path.join(download_dir, "model.keras")
        shutil.copy2(src, dst)
        return dst

    def load_joblib(self, key_prefix: str, filename: str, download_dir: str):
        src = os.path.join(self.base_dir, key_prefix, filename)
        dst = os.path.join(download_dir, filename)
        shutil.copy2(src, dst)
        return joblib.load(dst)

    def save_tfjs_model(self, model, key_prefix: str):
        try:
            import tensorflowjs as tfjs
            tfjs_dir = os.path.join(self.base_dir, key_prefix, "tfjs")
            os.makedirs(tfjs_dir, exist_ok=True)
            tfjs.converters.save_keras_model(model, tfjs_dir)
            print(f"[LocalStore] TFJS model -> {tfjs_dir}")
        except ImportError:
            print("[WARN] tensorflowjs not installed — skipping TFJS export.")
        except Exception as e:
            print(f"[ERROR] TFJS local export failed: {e}")


def get_artifact_store() -> ArtifactStore:
    return S3ArtifactStore() if settings.USE_S3 else LocalArtifactStore()
