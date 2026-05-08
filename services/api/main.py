from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from services.api.routes import endpoints

COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]


# ---------------------------------------------------------------------------
# Lifespan: pre-warm all models BEFORE accepting requests
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once at startup. Paid instances can prewarm all models; Render free
    tier stays lazy to avoid memory-limit restarts.
    """
    from shared.core.config import settings
    from shared.ml.registry import get_model_registry
    registry = get_model_registry()
    if settings.PREWARM_MODELS:
        print("[Startup] Pre-warming models ...")
        registry.prewarm_all(COINS)
        print("[Startup] All models ready OK")
    else:
        print("[Startup] Model prewarm disabled; loading models lazily")
    yield
    # Shutdown cleanup
    registry.dispose()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CryptoQuant API",
    version="v2.0.0",
    lifespan=lifespan,
)

# Compress responses > 1 KB automatically
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://cryptoquant.vercel.app",
        # Add your custom domain here — remove the wildcard in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"status": "online", "message": "CryptoQuant API", "version": "v2.0.0"}


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running"}


# Mount all routes
app.include_router(endpoints.router, prefix="/api/v1")
