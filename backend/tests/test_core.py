from app.services.anomaly_detector import AnomalyDetector
from app.services.sensor_simulator import SensorSimulator

def test_simulator_returns_valid_reading():
    reading = SensorSimulator(0).next_reading()
    assert 50 < reading.heart_rate < 110
    assert 90 < reading.spo2 <= 100

def test_magnitude_is_calculated():
    reading = SensorSimulator(0).next_reading()
    assert AnomalyDetector.magnitude(reading) > 0

def test_controlled_anomaly_is_detected():
    simulator, detector = SensorSimulator(0), AnomalyDetector()
    simulator.trigger_anomaly()
    detected = [detector.evaluate(simulator.next_reading())[0] for _ in range(5)]
    assert any(detected)
