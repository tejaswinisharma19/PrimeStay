
def test_homepage_returns_success(client):

    response = client.get("/")

    assert response.status_code == 200


def test_database_health_returns_success(client):

    response = client.get("/health/db")

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "connected"
