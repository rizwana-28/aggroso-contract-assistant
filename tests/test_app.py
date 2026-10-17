import os
import tempfile
import pytest
from app import app, init_db

@pytest.fixture()
def client():
    db_fd, path = tempfile.mkstemp()
    os.environ["DATABASE_PATH"] = path
    # app module DB_PATH is set at import, so use its current path for this test run.
    import app as app_module
    app_module.DB_PATH = path
    app_module.app.config["TESTING"] = True
    app_module.init_db()
    with app_module.app.test_client() as client:
        yield client
    os.close(db_fd)
    os.unlink(path)

def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"

def test_contract_validation(client):
    response = client.post("/api/contracts", json={"title": "Short", "contract_text": "too short"})
    assert response.status_code == 400

def test_create_and_review_obligation(client):
    response = client.post("/api/contracts", json={
        "title": "Test Services Agreement",
        "counterparty": "Example Co",
        "contract_text": "The customer must make payment within 30 days. The agreement will renew on 2027-03-01 unless notice is provided."
    })
    assert response.status_code == 201
    obligations = client.get("/api/obligations").get_json()
    assert len(obligations) >= 1
    oid = obligations[0]["id"]
    updated = client.patch(f"/api/obligations/{oid}", json={
        "status": "Approved", "reviewer_note": "Checked against source", "due_date": "2027-03-01"
    })
    assert updated.status_code == 200
    assert client.get("/api/obligations").get_json()[0]["status"] == "Approved"
