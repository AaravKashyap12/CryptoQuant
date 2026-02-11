
import sys
import os
import requests
import time


API_URL = "http://localhost:8001/api/v1"
COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]

def wait_for_server():
    print("Waiting for server to be ready...")
    for i in range(20):
        try:
            health = requests.get(f"{API_URL.replace('/api/v1', '')}/health", timeout=2)
            if health.status_code == 200:
                print("Server is UP and READY! \u2705") # Green Check
                return True
        except:
            pass
        time.sleep(1)
        print(f"Waiting... ({i+1}/20)")
    return False

def train_all():
    print("Triggering retraining for ALL coins on REAL data...")
    
    if not wait_for_server():
        print("Server timed out. Please ensure run_app.bat is running.")
        return

    for coin in COINS:
        try:
            print(f"--> Starting training for {coin}...")
            response = requests.post(f"{API_URL}/train/{coin}")
            if response.status_code == 200:
                print(f"    [OK] {coin} training started.")
            else:
                print(f"    [FAIL] {coin} failed: {response.text}")
        except Exception as e:
            print(f"    [ERROR] Could not connect to backend: {e}")
            
    print("\nAll training tasks queued. Models will update in ~5-10 minutes.")
    print("Monitor progress at: http://localhost:8001/api/v1/train-status/{coin}")

if __name__ == "__main__":
    train_all()
