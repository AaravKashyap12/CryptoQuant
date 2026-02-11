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
    allow_origins=["*"], # Allow ALL origins
    allow_credentials=False, # Must be False for wildcard origin
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Crypto Price Predictor API",
        "version": "v1.2.0-cors-fix",
        "last_updated": "2026-02-11T18:00:00"
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running \U0001F680"}

from app.api import endpoints

# app.include_router(endpoints.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """
    Server Startup:
    Auto-Pilot is DISABLED by default. Use /train endpoint manually.
    """
    print(" [INFO] Server starting... Auto-train disabled for stability.")

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    print(f" [INFO] Starting Uvicorn on port: {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
