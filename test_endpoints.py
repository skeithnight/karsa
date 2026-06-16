from fastapi.testclient import TestClient
from karsa.app import app
import json

with TestClient(app) as client:
    print("--- CIO DECISIONS ---")
    res1 = client.get("/cio/decisions")
    print("Status:", res1.status_code)
    print(json.dumps(res1.json(), indent=2))

    print("\n--- POST MORTEM RECORDS ---")
    res2 = client.get("/post-mortem/records")
    print("Status:", res2.status_code)
    print(json.dumps(res2.json(), indent=2))

    print("\n--- PORTFOLIO SUMMARY ---")
    res3 = client.get("/portfolio/summary")
    print("Status:", res3.status_code)
    print(json.dumps(res3.json(), indent=2))
