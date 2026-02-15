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
    print(" [INFO] Server starting... Background pre-warming initiated.")
    from shared.ml.registry import get_model_registry
    import asyncio
    
    registry = get_model_registry()
    
    def prewarm_task():
        for coin in ["BTCUSDT", "ETHUSDT"]:
            try:
                print(f" [INFO] Pre-warming {coin} model...")
                registry.load_latest_model(coin)
            except Exception as e:
                print(f" [WARN] Could not pre-warm {coin}: {e}")
        print(" [INFO] Pre-warming complete.")

    # Start pre-warming in a background thread so it doesn't block server startup
    asyncio.create_task(asyncio.to_thread(prewarm_task))

# async def train_coin_async(coin): ... MOVED TO WORKER

# No unvicorn.run here - managed by Docker CMD
