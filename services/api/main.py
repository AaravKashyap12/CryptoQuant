from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from services.api.routes import endpoints
from shared.core.config import settings

COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup only when the deployment has enough memory."""
    from shared.ml.registry import get_model_registry

    registry = get_model_registry()
    if settings.PREWARM_MODELS:
        print("[Startup] Pre-warming models ...")
        registry.prewarm_all(COINS)
        print("[Startup] All models ready OK")
    else:
        print("[Startup] Model prewarm disabled; loading models lazily")
    yield
    registry.dispose()


app = FastAPI(
    title="CryptoQuant API",
    version="v2.0.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

allowed_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def uncaught_exception_handler(request: Request, exc: Exception):
    origin = request.headers.get("origin")
    response = JSONResponse(
        status_code=500,
        content={"detail": str(exc) if settings.DEBUG else "Internal server error"},
    )
    if origin and (origin in allowed_origins or origin.endswith(".vercel.app")):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@app.get("/")
def read_root():
    return {"status": "online", "message": "CryptoQuant API", "version": "v2.0.0"}


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running"}


app.include_router(endpoints.router, prefix="/api/v1")
