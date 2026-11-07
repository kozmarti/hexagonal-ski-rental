def test_home_page_responds(client):
    response = client.get("/")

    assert response.status_code == 200
