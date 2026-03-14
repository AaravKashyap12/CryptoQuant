from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
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
    Runs once at startup. Loads all 5 coin models into the registry cache
    so the first user request is never a cold-load.
    """
    from shared.ml.registry import get_model_registry
    registry = get_model_registry()
    print("[Startup] Pre-warming models ...")
    registry.prewarm_all(COINS)
    print("[Startup] All models ready OK")
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
    return {"status": "ok", "message": "Backend is running 🚀"}


# Mount all routes
app.include_router(endpoints.router, prefix="/api/v1")
