from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router
# Force reload trigger
app = FastAPI(
    title="Crypto Price Predictor API",
    description="Backend API for LSTM Crypto Price Prediction",
    version="1.0.0"
)

# CORS Code
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://cryptoquant.vercel.app", # Explicit Vercel Domain
    "https://crypto-quant-orcin.vercel.app", # Previous Vercel Domain (just in case)
    "*", # Allow all for now during debug, but specific domains above are preferred
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Crypto Price Predictor API",
        "version": "v1.1.0-fix-symbol",
        "last_updated": "2026-02-11T17:30:00"
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running 🚀"}

from app.api import endpoints

app.include_router(endpoints.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """
    On startup, trigger a background task to retrain models if they are missing or old.
    This ensures the app is always "fresh" without manual scripts.
    """
    import threading
    import time
    from src.train_model import train_single_coin
    
    def training_loop():
        while True:
            print(" [AUTO-TRAIN] Starting daily model update... ")
            coins = ["BTC", "ETH", "BNB", "SOL", "ADA"]
            for coin in coins:
                try:
                    train_single_coin(f"{coin}USDT")
                except Exception as e:
                    print(f" [AUTO-TRAIN] Failed {coin}: {e}")
            print(" [AUTO-TRAIN] Complete. Serving fresh models. Sleeping for 24 hours...")
            time.sleep(86400) # 24 Hours
        
    # Start in background thread
    train_thread = threading.Thread(target=training_loop, daemon=True)
    train_thread.start()
