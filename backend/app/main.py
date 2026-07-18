from __future__ import annotations
import asyncio, logging, uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import Base, engine
from app.db.repository import EventRepository, get_event_repository
from app.models.anomaly import AnomalyEvent
from app.services.anomaly_detector import AnomalyDetector
from app.services.connection_manager import ConnectionManager
from app.services.llm_service import LLMProvider, get_llm_provider
from app.services.sensor_simulator import SensorSimulator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
manager, simulator, detector = ConnectionManager(), SensorSimulator(settings.anomaly_frequency), AnomalyDetector()
repository: EventRepository = get_event_repository()
llm: LLMProvider = get_llm_provider()
last_llm_at = 0.0

async def generate_insight(event: AnomalyEvent) -> None:
    await manager.broadcast("llm_stream_start", {"event_id": event.event_id})
    chunks = []
    try:
        async for chunk in llm.stream_insight(event):
            chunks.append(chunk); await manager.broadcast("llm_stream_chunk", {"event_id": event.event_id, "chunk": chunk})
        await repository.update_event_insight(event.event_id, "".join(chunks))
        await manager.broadcast("llm_stream_end", {"event_id": event.event_id})
        logger.info("LLM streaming completed for %s", event.event_id)
    except Exception as exc:
        logger.exception("LLM streaming failed")
        await manager.broadcast("llm_stream_error", {"event_id": event.event_id, "message": str(exc)})

async def sensor_loop() -> None:
    global last_llm_at
    while True:
        reading = simulator.next_reading()
        await manager.broadcast("sensor_update", reading.model_dump(mode="json"))
        try:
            anomalous, score, confidence, magnitude = detector.evaluate(reading)
            now = asyncio.get_running_loop().time()
            if anomalous and now - last_llm_at >= settings.anomaly_cooldown_seconds:
                event = AnomalyEvent(event_id=str(uuid.uuid4()), timestamp=reading.timestamp, heart_rate=reading.heart_rate, spo2=reading.spo2, accelerometer_magnitude=magnitude, anomaly_score=score, confidence=confidence, severity="high" if confidence >= .65 else "medium")
                await repository.save_event(event); last_llm_at = now
                await manager.broadcast("anomaly_detected", event.model_dump(mode="json"))
                logger.info("Anomaly detected confidence=%.2f", confidence)
                asyncio.create_task(generate_insight(event))
        except Exception: logger.exception("Anomaly evaluation failed; stream continues")
        await asyncio.sleep(settings.sensor_interval_seconds)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if repository.provider_name == "sqlite": Base.metadata.create_all(engine)
    task = asyncio.create_task(sensor_loop())
    logger.info("application_started model_loaded=true repository=%s llm_provider=%s", repository.provider_name, llm.provider_name)
    try: yield
    finally:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        logger.info("application_shutdown")

app = FastAPI(title="PulseGuard AI", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_allowed_origins, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health(): return {"status": "healthy"}
@app.get("/ready")
def ready(): return {"status": "ready", "model_loaded": True, "sensor_service_initialized": True, "event_repository": repository.provider_name}
@app.get("/api/status")
def status(): return {"status":"ok", "llm_provider":llm.provider_name, "event_repository":repository.provider_name, "model_loaded":True, "active_websocket_connections":len(manager.connections)}
@app.get("/api/events")
async def events(limit: int = 30): return await repository.list_events(min(max(limit, 1), 100))
@app.get("/api/events/{event_id}")
async def event(event_id: str):
    result = await repository.get_event(event_id)
    if not result: raise HTTPException(404, "Event not found")
    return result
@app.post("/api/demo/trigger-anomaly")
def trigger_anomaly(): return {"scenario": simulator.trigger_anomaly(), "message":"Next readings will be abnormal"}
@app.websocket("/ws/live")
async def live_socket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.disconnect(websocket)
