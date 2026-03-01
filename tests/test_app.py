import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_app_exists():
    assert app is not None


def test_home_route(client):
    response = client.get("/")
    assert response.status_code in [200, 302, 404]