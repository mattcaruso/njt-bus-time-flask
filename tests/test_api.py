import os
import pytest
from api import app
from api.app import render_pixlet, push_to_tidbyt, next_departures


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_index(client):
    assert client.get("/").status_code == 200


def test_health(client):
    assert client.get("/health").status_code == 200


def test_next_departure(client):
    assert client.get(f"/stops/{21055}/{123}/next_departures").status_code == 200  # TODO Generalize tests


def test_next_departures():
    departures = next_departures('21073', '84')
    pass


def test_render_via_axilla():
    assert type(render_pixlet()) == str


def test_push_to_tidbyt_type_error():
    with pytest.raises(TypeError) as exc:
        push_to_tidbyt('test-device-id')  # noQA, will get type error

    assert exc.type == TypeError
    assert str(exc.value) == 'device_ids must be provided as a list'


def test_push_to_tidbyt():
    response = push_to_tidbyt(','.split(os.environ['TIDBYT_DEVICE_IDS']))
    assert response.status_code == 200
