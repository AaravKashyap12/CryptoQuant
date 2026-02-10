import requests
import json

try:
    response = requests.post("http://localhost:8000/api/v1/predict/BTC")
    print("Status Code:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(response.text)
except Exception as e:
    print("Error:", e)
