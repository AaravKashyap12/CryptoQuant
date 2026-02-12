import os
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Minimal Diagnostic App v2",
        "port_bound": os.environ.get("PORT", "unknown"),
        "env_vars": dict(os.environ)
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    # Use the PORT environment variable provided by Railway
    port = int(os.environ.get("PORT", 8080))
    print(f" [DIAGNOSTIC] Starting Uvicorn on port: {port} with Interface 0.0.0.0")
    uvicorn.run(app, host="0.0.0.0", port=port)
