from fastapi.testclient import TestClient
from app.main import app

def next_sensor(socket):
    for _ in range(100):
        message = socket.receive_json()
        if message["type"] == "sensor_update":
            return message
    raise AssertionError("No sensor update received")

def test_health_and_demo_endpoints():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "healthy"}
        assert client.get("/ready").json()["status"] == "ready"
        response = client.post("/api/demo/trigger-anomaly")
        assert response.status_code == 200
        assert response.json()["scenario"] in {"high_heart_rate", "low_spo2", "high_movement", "combined"}


def test_two_websocket_clients_receive_the_shared_stream_after_one_disconnect():
    """Regression check for the single-producer, multi-observer design."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/live") as first:
          with client.websocket_connect("/ws/live") as second:
            one = next_sensor(first)
            two = next_sensor(second)
            assert one["type"] == two["type"] == "sensor_update"
          # The second client closed; the producer must still serve the first.
          assert next_sensor(first)["type"] == "sensor_update"
