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
    print(" [INFO] Server starting... Auto-train disabled for stability.")

# No unvicorn.run here - managed by Docker CMD
