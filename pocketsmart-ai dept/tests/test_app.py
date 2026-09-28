"""
End-to-end tests for PocketSmart AI.

Run with the project's GEMINI_API_KEY unset (or in a clean env) so the
app operates in MOCK MODE - this way tests are fast, free, and don't
depend on network access, while still exercising the full
register -> login -> generate -> history pipeline.

    pytest -v
"""
import io
import os
import uuid

os.environ.setdefault("GEMINI_API_KEY", "")  # force mock mode for tests

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _unique_username() -> str:
    return "tester_" + uuid.uuid4().hex[:8]


def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_landing_page_loads():
    res = client.get("/")
    assert res.status_code == 200
    assert "PocketSmart" in res.text


def test_register_login_and_dashboard_flow():
    username = _unique_username()
    res = client.post(
        "/register",
        data={
            "username": username,
            "email": f"{username}@example.com",
            "full_name": "Test User",
            "password": "supersecret",
            "confirm_password": "supersecret",
        },
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert "access_token" in res.cookies

    # Dashboard should now be reachable with the session cookie.
    dash = client.get("/dashboard")
    assert dash.status_code == 200
    assert "Test User" in dash.text


def _register_and_get_client() -> TestClient:
    c = TestClient(app)
    username = _unique_username()
    c.post(
        "/register",
        data={
            "username": username,
            "email": f"{username}@example.com",
            "full_name": "Fixture User",
            "password": "supersecret",
            "confirm_password": "supersecret",
        },
    )
    c.username = username
    return c


def test_token_endpoint_oauth2_flow():
    username = _unique_username()
    client.post(
        "/register",
        data={
            "username": username,
            "email": f"{username}@example.com",
            "full_name": "Token User",
            "password": "supersecret",
            "confirm_password": "supersecret",
        },
    )
    res = client.post("/token", data={"username": username, "password": "supersecret"})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_generate_home_recommendations():
    c = _register_and_get_client()
    payload = {
        "budget": 50000,
        "currency": "INR",
        "style_preference": "Modern",
        "rooms": [
            {"room_type": "Living Room", "lights": 3, "ceiling_fans": 1, "sofas": 1},
            {"room_type": "Bedroom", "lights": 2, "wardrobes": 1},
        ],
        "preferred_platforms": ["Amazon", "IKEA"],
    }
    res = c.post("/generate-home", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["planner_type"] == "home"
    assert len(data["items"]) > 0
    assert data["source"] in ("gemini", "fallback")
    for item in data["items"]:
        assert item["search_link"].startswith("https://")


def test_generate_party_recommendations():
    c = _register_and_get_client()
    payload = {
        "budget": 80000,
        "currency": "INR",
        "guest_count": 40,
        "event_type": "Birthday",
        "venue_city": "Coimbatore",
        "needs_accommodation": False,
        "preferred_platforms": ["Swiggy", "Zomato"],
    }
    res = c.post("/generate-party", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["planner_type"] == "party"
    assert len(data["items"]) >= 3


def test_generate_jewelry_recommendations_without_image():
    c = _register_and_get_client()
    res = c.post(
        "/generate-jewelry",
        data={
            "budget": "30000",
            "currency": "INR",
            "occasion": "Wedding",
            "style_preference": "Traditional",
            "metal_preference": "Gold",
            "preferred_platforms": "Amazon,Flipkart",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["planner_type"] == "jewelry"
    assert len(data["items"]) > 0


def test_generate_jewelry_recommendations_with_image():
    c = _register_and_get_client()
    fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 100)
    res = c.post(
        "/generate-jewelry",
        data={
            "budget": "30000",
            "currency": "INR",
            "occasion": "Festival",
            "preferred_platforms": "Amazon,Flipkart",
        },
        files={"outfit_image": ("outfit.png", fake_image, "image/png")},
    )
    # A malformed fake PNG should not crash the endpoint - it should
    # gracefully fall back to text-only recommendations.
    assert res.status_code == 200


def test_history_tracks_generated_recommendations():
    c = _register_and_get_client()
    c.post(
        "/generate-party",
        json={
            "budget": 20000,
            "currency": "INR",
            "guest_count": 10,
            "event_type": "Anniversary",
        },
    )
    res = c.get("/api/history")
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == c.username
    assert len(data["history"]) >= 1


def test_session_info_and_session_data():
    c = _register_and_get_client()
    info = c.get("/session-info")
    assert info.status_code == 200
    assert info.json()["logged_in"] is True

    session_data = c.get("/session-data")
    assert session_data.status_code == 200
    assert "total_recommendations" in session_data.json()


def test_unauthenticated_access_redirects_to_login():
    anon = TestClient(app)
    res = anon.get("/dashboard", follow_redirects=False)
    assert res.status_code in (302, 303, 307)
    assert res.headers["location"] == "/login"
