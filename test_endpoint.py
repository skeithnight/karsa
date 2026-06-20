from karsa.app import app
from fastapi.testclient import TestClient

client = TestClient(app)
try:
    response = client.get("/portfolio/summary")
    print("Status:", response.status_code)
    print("Body:", response.text)
except Exception as e:
    import traceback
    traceback.print_exc()
