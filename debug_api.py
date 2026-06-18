import traceback
import sys
import os

sys.path.insert(0, os.path.abspath('src'))

from fastapi.testclient import TestClient
from karsa.app import app

def main():
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            try:
                response = client.get("/cio/decisions?page=1&size=50")
                print("CIO Decisions:", response.status_code)
                print(response.json())
            except Exception as e:
                print("CIO Decisions Exception:")
                traceback.print_exc()

            try:
                response = client.get("/post-mortem/records?limit=50")
                print("Post Mortem:", response.status_code)
                print(response.json())
            except Exception as e:
                print("Post Mortem Exception:")
                traceback.print_exc()
    except Exception as e:
        print("Lifespan or startup exception:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
