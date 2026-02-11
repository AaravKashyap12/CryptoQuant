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
    return {"message": "CryptoQuant API is running! 🚀", "docs_url": "/docs"}

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running 🚀"}

from app.api import endpoints

app.include_router(endpoints.router, prefix="/api/v1")
