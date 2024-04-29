import pytest
from api.app import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_index(client):
    assert client.get("/").status_code == 200


def test_health(client):
    assert client.get("/health").status_code == 200


def test_next_departure(client):
    assert client.get(f"/stops/{21055}/{123}/next_departures").status_code == 200
