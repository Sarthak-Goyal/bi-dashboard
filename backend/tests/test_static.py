"""Single-container mode: the API process also serves the built React app."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_root_and_client_side_routes_serve_the_spa(client):
    for path in ("/", "/crime", "/housing", "/some/deep/link"):
        r = client.get(path)
        assert r.status_code == 200 and 'id="root"' in r.text, path


def test_real_files_are_served(client):
    r = client.get("/assets/app.js")
    assert r.status_code == 200 and "console.log" in r.text


def test_unknown_api_paths_404_instead_of_returning_the_spa(client):
    assert client.get("/api/nope").status_code == 404
    assert client.get("/api/metrics/nope").status_code == 404


@pytest.mark.parametrize("path", [
    "/../secret.txt", "/..%2fsecret.txt", "/assets/../../secret.txt", "/%2e%2e/secret.txt",
])
def test_path_traversal_cannot_escape_the_static_dir(client, path):
    r = client.get(path)
    assert "TOP-SECRET" not in r.text


def test_api_still_wins_over_the_spa_fallback(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/docs").status_code == 200
