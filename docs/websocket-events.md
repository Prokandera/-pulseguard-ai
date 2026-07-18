# WebSocket events

All messages use `{ "type": string, "data": object }` on `ws://localhost:8000/ws/live`.

| Type | Data |
|---|---|
| `sensor_update` | timestamp, heart_rate, spo2, accelerometer |
| `anomaly_detected` | event_id, score, confidence, severity, metrics |
| `llm_stream_start` | event_id |
| `llm_stream_chunk` | event_id, chunk |
| `llm_stream_end` | event_id |
| `llm_stream_error` | event_id, message |
