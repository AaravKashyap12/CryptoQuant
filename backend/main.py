from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints

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
    from src.registry import ModelRegistry
    from src.train_model import train_single_coin
    import asyncio
    
    registry = ModelRegistry()
    
    # Check if BTC model exists as a proxy for all
    if registry.get_latest_version("BTCUSDT") == "v0.0.0":
        print(" [WARN] No models found! Triggering background training...")
        # We can't use BackgroundTasks here easily, so we launch an async task
        for coin in ["BTC", "ETH", "BNB", "SOL", "ADA"]:
            asyncio.create_task(train_coin_async(coin))

async def train_coin_async(coin):
    from src.train_model import train_single_coin
    print(f" [AUTO-TRAIN] Starting for {coin}...")
    try:
        train_single_coin(f"{coin}USDT")
    except Exception as e:
        print(f" [AUTO-TRAIN] Failed for {coin}: {e}")

# No unvicorn.run here - managed by Docker CMD
