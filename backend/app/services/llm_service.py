"""Streaming LLM providers. Each yields text chunks without response buffering."""
from __future__ import annotations
import asyncio, json, logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
import httpx
from app.core.config import settings
from app.models.anomaly import AnomalyEvent

logger = logging.getLogger(__name__)
SYSTEM_PROMPT = "You analyze simulated wearable data for a software demo. Be concise, observational, non-diagnostic, and state this is not medical advice."

class LLMProvider(ABC):
    provider_name: str
    @abstractmethod
    async def stream_insight(self, event: AnomalyEvent) -> AsyncIterator[str]: ...

class MockStreamingLLMProvider(LLMProvider):
    provider_name = "mock"
    async def stream_insight(self, event: AnomalyEvent) -> AsyncIterator[str]:
        message = (f"Simulated wearable data shows an unusual pattern: heart rate {event.heart_rate:.0f} BPM, SpO2 {event.spo2:.0f}%, and movement magnitude {event.accelerometer_magnitude:.1f}. This is an observational software-demo insight, not medical advice. If this were real and readings persisted, seek professional medical attention.")
        for word in message.split(" "):
            await asyncio.sleep(.045)
            yield word + " "

class OpenAICompatibleStreamingProvider(LLMProvider):
    provider_name = "openai"
    async def stream_insight(self, event: AnomalyEvent) -> AsyncIterator[str]:
        if not settings.llm_api_key: raise RuntimeError("LLM_API_KEY is required for LLM_PROVIDER=openai")
        payload = {"model": settings.llm_model, "stream": True, "messages": [{"role":"system", "content":SYSTEM_PROMPT}, {"role":"user", "content":f"Heart rate: {event.heart_rate:.0f} BPM; SpO2: {event.spo2:.0f}%; movement: {event.accelerometer_magnitude:.2f}; confidence: {event.confidence:.0%}."}]}
        headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream("POST", f"{settings.llm_base_url.rstrip('/')}/chat/completions", json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]": break
                        chunk = json.loads(data).get("choices", [{}])[0].get("delta", {}).get("content")
                        if chunk: yield chunk

class BedrockStreamingProvider(LLMProvider):
    provider_name = "bedrock"
    async def stream_insight(self, event: AnomalyEvent) -> AsyncIterator[str]:
        if not settings.bedrock_model_id: raise RuntimeError("BEDROCK_MODEL_ID is required for LLM_PROVIDER=bedrock")
        # boto3 streaming is synchronous; a worker thread forwards chunks to the async event loop.
        import boto3
        loop, queue = asyncio.get_running_loop(), asyncio.Queue[str | Exception | None]()
        def invoke() -> None:
            try:
                client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
                response = client.converse_stream(modelId=settings.bedrock_model_id, system=[{"text": SYSTEM_PROMPT}], messages=[{"role":"user", "content":[{"text": f"Heart rate: {event.heart_rate:.0f} BPM; SpO2: {event.spo2:.0f}%; movement: {event.accelerometer_magnitude:.2f}; confidence: {event.confidence:.0%}."}]}])
                for part in response["stream"]:
                    text = part.get("contentBlockDelta", {}).get("delta", {}).get("text")
                    if text: loop.call_soon_threadsafe(queue.put_nowait, text)
            except Exception as exc: loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally: loop.call_soon_threadsafe(queue.put_nowait, None)
        task = asyncio.create_task(asyncio.to_thread(invoke))
        try:
            while True:
                item = await queue.get()
                if item is None: break
                if isinstance(item, Exception): raise item
                yield item
        finally:
            await task

def get_llm_provider() -> LLMProvider:
    providers = {"mock": MockStreamingLLMProvider, "openai": OpenAICompatibleStreamingProvider, "bedrock": BedrockStreamingProvider}
    try: return providers[settings.llm_provider]()
    except KeyError as exc: raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}") from exc
