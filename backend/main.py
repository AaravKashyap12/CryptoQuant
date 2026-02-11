from fastapi import FastAPI
import uvicorn
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Minimal Diagnostic App",
        "port_bound": os.environ.get("PORT", "unknown")
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f" [DIAGNOSTIC] Starting Uvicorn on port: {port} with Interface 0.0.0.0")
    uvicorn.run(app, host="0.0.0.0", port=port)
