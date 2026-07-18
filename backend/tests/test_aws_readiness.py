import asyncio
from pathlib import Path
import pytest
from dotenv import dotenv_values
from app.core.config import settings
from app.db.repository import SQLiteEventRepository, get_event_repository
from app.services.llm_service import LLMProviderError, MockStreamingLLMProvider, OpenAICompatibleStreamingProvider, get_llm_provider


def test_local_defaults_use_optional_aws_safe_providers():
    assert isinstance(get_event_repository(), SQLiteEventRepository)
    assert isinstance(get_llm_provider(), MockStreamingLLMProvider)


def test_mock_provider_streams_more_than_one_chunk():
    from app.models.anomaly import AnomalyEvent
    from datetime import datetime, timezone
    event = AnomalyEvent(event_id="test", timestamp=datetime.now(timezone.utc), heart_rate=150, spo2=88, accelerometer_magnitude=2.5, anomaly_score=-0.2, confidence=.9, severity="high")
    async def collect(): return [chunk async for chunk in get_llm_provider().stream_insight(event)]
    assert len(asyncio.run(collect())) > 1


def test_openai_provider_selection_is_environment_driven():
    original = settings.llm_provider
    try:
        object.__setattr__(settings, "llm_provider", "openai")
        assert isinstance(get_llm_provider(), OpenAICompatibleStreamingProvider)
    finally:
        object.__setattr__(settings, "llm_provider", original)


def test_openai_provider_reports_missing_api_key_without_network_call():
    from app.models.anomaly import AnomalyEvent
    from datetime import datetime, timezone
    event = AnomalyEvent(event_id="test", timestamp=datetime.now(timezone.utc), heart_rate=150, spo2=88, accelerometer_magnitude=2.5, anomaly_score=-0.2, confidence=.9, severity="high")
    original = settings.llm_api_key
    async def consume():
        async for _ in OpenAICompatibleStreamingProvider().stream_insight(event): pass
    try:
        object.__setattr__(settings, "llm_api_key", None)
        with pytest.raises(LLMProviderError, match="LLM_API_KEY"):
            asyncio.run(consume())
    finally:
        object.__setattr__(settings, "llm_api_key", original)


def test_openrouter_local_example_has_no_secret_and_expected_provider_settings():
    values = dotenv_values(Path(__file__).resolve().parents[1] / ".env.example")
    assert values["LLM_PROVIDER"] == "openai"
    assert values["LLM_BASE_URL"] == "https://openrouter.ai/api/v1"
    assert values["LLM_MODEL"] == "openrouter/free"
    assert values["LLM_API_KEY"] == ""
