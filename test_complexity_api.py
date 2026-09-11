import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_complexity_endpoint_returns_json_without_image():
    r = client.post("/api/complexity", data={"description": "Tapu Bulu con corna, zampe, placche e dettagli"})
    assert r.headers["content-type"].startswith("application/json")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "ok"
    assert 0 <= body["result"]["score"] <= 100

def test_complexity_endpoint_rejects_invalid_image_as_json():
    r = client.post("/api/complexity", data={"description": "test"}, files={"image": ("bad.png", io.BytesIO(b"not an image"), "image/png")})
    assert r.status_code == 400
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["mode"] == "error"
    assert "immagine" in r.json()["error"].lower()
