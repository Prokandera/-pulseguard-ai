import asyncio
from app.db.repository import SQLiteEventRepository, get_event_repository
from app.services.llm_service import MockStreamingLLMProvider, get_llm_provider


def test_local_defaults_use_optional_aws_safe_providers():
    assert isinstance(get_event_repository(), SQLiteEventRepository)
    assert isinstance(get_llm_provider(), MockStreamingLLMProvider)


def test_mock_provider_streams_more_than_one_chunk():
    from app.models.anomaly import AnomalyEvent
    from datetime import datetime, timezone
    event = AnomalyEvent(event_id="test", timestamp=datetime.now(timezone.utc), heart_rate=150, spo2=88, accelerometer_magnitude=2.5, anomaly_score=-0.2, confidence=.9, severity="high")
    async def collect(): return [chunk async for chunk in get_llm_provider().stream_insight(event)]
    assert len(asyncio.run(collect())) > 1
