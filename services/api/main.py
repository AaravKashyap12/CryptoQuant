from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.api.routes import endpoints

app = FastAPI()

# Allow ANY origin (for simplicity/debugging)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Crypto Price Predictor API",
        "version": "v1.2.0-stable"
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running \U0001F680"}

# Include application routes
app.include_router(endpoints.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    print(" [INFO] Server starting... Checking model status.")
    from shared.ml.registry import get_model_registry
    import asyncio
    
    registry = get_model_registry()
    
    # Warm up cache for BTC and ETH
    for coin in ["BTCUSDT", "ETHUSDT"]:
        print(f" [INFO] Pre-warming cache for {coin}...")
        registry.load_latest_model(coin)
    
    # Check if BTC model exists as a proxy for all
    if registry.get_latest_version("BTCUSDT") == "v0.0.0":
        print(" [WARN] No models found! Triggering background training via Worker...")
        # TODO: Trigger worker job instead of internal training
        pass

# async def train_coin_async(coin): ... MOVED TO WORKER

# No unvicorn.run here - managed by Docker CMD
