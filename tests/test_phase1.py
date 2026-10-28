import os
import sys

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.db.init_db import init_db

init_db()
client = TestClient(app)

def test_health():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_auth_and_farm_flow():
    # 1. Signup
    signup_payload = {
        "email": "testfarmer@agrimind.ai",
        "password": "Password123!",
        "full_name": "Karthik Farmer",
        "role": "farmer"
    }
    res = client.post("/api/v1/auth/signup", json=signup_payload)
    assert res.status_code in [201, 400] # 400 if already created
    if res.status_code == 400:
        login_res = client.post("/api/v1/auth/login", json={"email": "testfarmer@agrimind.ai", "password": "Password123!"})
        token = login_res.json()["access_token"]
    else:
        token = res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Me
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "testfarmer@agrimind.ai"

    # 3. Create Farm
    farm_payload = {
        "name": "Green Acres Demo Farm",
        "location": "Karnataka, India",
        "area_acres": 5.5,
        "soil_type": "Black Clay"
    }
    res_farm = client.post("/api/v1/farms", json=farm_payload, headers=headers)
    assert res_farm.status_code == 201
    farm_id = res_farm.json()["id"]

    # 4. List Farms
    res_farms = client.get("/api/v1/farms", headers=headers)
    assert res_farms.status_code == 200
    assert len(res_farms.json()) >= 1

    # 5. Add Crop
    crop_payload = {
        "name": "Wheat",
        "variety": "HD 2967",
        "planting_date": "2026-01-15",
        "status": "Healthy",
        "notes": "Optimal irrigation applied"
    }
    res_crop = client.post(f"/api/v1/farms/{farm_id}/crops", json=crop_payload, headers=headers)
    assert res_crop.status_code == 201
    assert res_crop.json()["name"] == "Wheat"

    print("Phase 1 verification passed successfully!")

if __name__ == "__main__":
    test_health()
    test_auth_and_farm_flow()
