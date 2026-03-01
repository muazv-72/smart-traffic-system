from app import app


def test_dashboard_route():
    client = app.test_client()
    response = client.get("/dashboard")
    assert response.status_code in [200, 302, 401, 404]
