# Walkthrough notes

## 60-second introduction

“PulseGuard AI simulates one wearable device stream, uses Isolation Forest to identify unusual combinations of heart rate, oxygen saturation, and movement, and sends every browser live updates over WebSockets. Significant events are stored in SQLite. The insight is generated in a separate async task and streamed chunk by chunk, so charts keep moving while text appears.”

## Key explanations

- FastAPI lifespan starts the model, database, and one shared producer task.
- `ConnectionManager` owns browser sockets and a failed client is removed without affecting others.
- `useWearableSocket` reconnects with capped exponential backoff and keeps only 60 chart points.
- SQLite persists anomalies only; normal readings are transient.
- In production, use authentication, TLS, proper CORS, encrypted/managed storage, real monitored data validation, and Redis Pub/Sub for multi-instance broadcasting.

## Interview questions and answers

1. **Why WebSockets instead of REST polling?** WebSockets push telemetry with low latency and avoid repeated polling. REST remains useful for stable resources such as event history.
2. **Why WebSockets instead of SSE?** SSE is good for one-way streaming; WebSockets support future client commands too, while handling the same live feed.
3. **What starts at backend startup?** FastAPI creates SQLite tables, starts the shared sensor loop, and keeps the trained model in memory.
4. **Why one sensor producer?** Every dashboard observes the same simulated wearable and a new browser does not multiply background work.
5. **What does `asyncio.create_task` achieve?** It lets LLM streaming run concurrently, so the sensor loop never waits for it.
6. **Does async make CPU work faster?** No. It makes I/O waiting concurrent; the small model inference is fast enough to run directly here.
7. **How are disconnected clients handled?** `WebSocketDisconnect` and send failures remove only that socket from the connection set.
8. **What is backpressure here?** A slow client can delay a send. A one-second send timeout drops it rather than blocking all healthy clients.
9. **Why Isolation Forest?** It finds outliers without labelled anomaly examples and remains small enough to explain in a hackathon walkthrough.
10. **Which model features are used?** Heart rate, SpO2, and accelerometer magnitude `sqrt(x²+y²+z²)`.
11. **How is training data made?** The backend creates reproducible synthetic normal distributions at startup using a fixed random seed.
12. **What is an anomaly score?** Isolation Forest’s decision score; values below zero lie outside its learned normal region.
13. **Is confidence a medical probability?** No. It normalizes model distance to a 0–1 UI indicator and is strictly demonstrative.
14. **Why have transparent hard bounds too?** They guarantee clearly extreme demo readings trigger despite limits of synthetic training data; Isolation Forest still evaluates every reading.
15. **Why a cooldown?** It prevents near-identical readings from repeatedly triggering costly, noisy LLM insights.
16. **Why use mock LLM streaming?** The full UI works without credentials, while small delayed chunks demonstrate actual incremental rendering.
17. **How is real streaming not buffered?** Each OpenAI-compatible SSE line is parsed and immediately yielded to WebSocket broadcast before later chunks arrive.
18. **How are provider errors shown?** The async task catches errors and sends `llm_stream_error`; it does not stop telemetry.
19. **Why persist only anomaly events?** Normal second-by-second telemetry has little initial demo value and would create unnecessary storage growth.
20. **Why SQLite?** It is local, transparent, and requires no service; production would normally use managed relational storage.
21. **How does React update without reloads?** The socket hook receives typed events and updates component state, which causes React to rerender affected charts and panels.
22. **Why cap the chart to 60 readings?** It gives a readable minute of context while bounding memory and chart rendering work.
23. **How does reconnection work?** The hook reconnects with capped exponential delay and cleans up its socket/timer on unmount.
24. **How are invalid events handled?** The client catches JSON parsing problems, logs a development warning, and leaves the dashboard usable.
25. **How would multiple backend instances work?** Use Redis Pub/Sub or another shared broker so every instance receives the single stream and broadcasts it locally.
26. **Why might sticky sessions be used?** They can simplify socket routing, but shared pub/sub is still required for cross-instance event delivery.
27. **What security is intentionally local-only?** There is no authentication, TLS, origin allowlist beyond localhost, rate limiting, or validated device identity yet.
28. **What production WebSocket protections are needed?** HTTPS/WSS, authenticated sessions, origin validation, rate limits, message size limits, monitoring, and durable queues.
29. **What are the ML limitations?** Synthetic data, simplified features, and no personal baseline mean it cannot provide clinical conclusions.
30. **What would improve this next?** Real consented data, calibrated models, clinician review, authenticated device ingestion, Redis scaling, and observability.

### Deeper technical answers

1. A persistent socket amortizes connection setup and lets the server broadcast immediately; REST endpoints are intentionally reserved for finite request/response data.
2. SSE has simpler HTTP semantics but cannot naturally receive client messages; this protocol uses one envelope regardless of direction.
3. The lifespan function runs before requests, creates schema once, and retains a task reference so shutdown can cancel it.
4. The simulator’s mutable state evolves one sequence; every socket receives the same serialized reading from `ConnectionManager.broadcast`.
5. The task is scheduled on the same event loop and yields during network/chunk waits, allowing the producer’s next sleep and broadcast to run.
6. CPU-heavy work would require a worker process or thread pool; putting it in the event loop would stall every WebSocket client.
7. The manager stores sockets in a set, discards them idempotently, and does not let cleanup exceptions escape into the producer loop.
8. Production systems may use per-client queues and explicit policies; this prototype chooses a clear timeout-and-disconnect policy.
9. Isolation Forest isolates unusual samples through random feature splits, so unusually short average paths indicate outliers.
10. Magnitude compresses three accelerometer dimensions into an understandable movement feature, avoiding an unnecessarily complex first model.
11. The fixed seed makes model behavior reproducible in a walkthrough, while Gaussian noise supplies realistic variation around normal baselines.
12. The raw score preserves useful model detail; only the UI-facing confidence is clamped and simplified.
13. It has no calibration against clinical outcomes, so interpreting it as risk or diagnosis would be unsafe.
14. The rules are deliberately visible in code and apply only to extreme values, rather than hiding a second opaque model.
15. The loop still broadcasts and evaluates data during cooldown; it suppresses only creation of a new LLM task.
16. Both mock and real providers expose the same async iterator contract, keeping the WebSocket flow identical in demos and configured runs.
17. The provider iterates `httpx` response lines, parses `data:` SSE payloads, and yields `delta.content` as soon as it appears.
18. Partial text remains visible when a provider fails, while the error event lets the UI stop its streaming indicator safely.
19. Persisting only meaningful events reduces write amplification; a production telemetry product could add a time-series store separately.
20. SQLAlchemy maps a small event table with timestamps, scores, metrics, severity, and final text, giving the UI refresh-safe history.
21. The event union gives TypeScript known data shapes, so sensor, anomaly, and chunk state updates are explicit rather than loosely typed.
22. Slicing before appending creates a new bounded array, preventing a long demo session from degrading browser performance.
23. The callback is stored in a ref so reconnection does not depend on unstable render callbacks or accidentally create duplicate sockets.
24. Parsing is guarded at the browser boundary; server protocol changes should also be documented and versioned in a larger system.
25. Redis would distribute events between processes; each process would keep only its local connected sockets and relay broker messages to them.
26. Socket affinity minimizes reconnect churn, but it cannot replace a broker because events can originate on any worker.
27. The CORS list permits the Vite origin only; production must authenticate sockets before accepting them and protect data at rest/in transit.
28. Operational protections also include connection quotas, audit logs, health checks, alerting, and safe provider timeout/retry policies.
29. A real wearable model needs representative labelled validation, individual baselines, drift monitoring, and explicit safety governance.
30. Those changes separate a learning prototype from a reliable health product and require domain, privacy, and security review.
