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

class LLMProviderError(RuntimeError):
    """A safe, UI-facing provider error. Never include credentials in it."""

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
        if not settings.llm_api_key:
            raise LLMProviderError("LLM_PROVIDER=openai requires LLM_API_KEY. Add it to backend/.env locally or inject it through Secrets Manager in ECS.")
        payload = {"model": settings.llm_model, "stream": True, "messages": [{"role":"system", "content":SYSTEM_PROMPT}, {"role":"user", "content":f"Heart rate: {event.heart_rate:.0f} BPM; SpO2: {event.spo2:.0f}%; movement: {event.accelerometer_magnitude:.2f}; confidence: {event.confidence:.0%}."}]}
        headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
        endpoint = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
        timeout = httpx.Timeout(connect=10, read=60, write=30, pool=10)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                    if response.status_code == 401:
                        logger.error("llm_authentication_failed provider=openai status=401")
                        raise LLMProviderError("LLM authentication failed. Check LLM_API_KEY without logging or sharing it.")
                    if response.status_code == 429:
                        logger.warning("llm_rate_limited provider=openai retry_after=%s", response.headers.get("Retry-After"))
                        raise LLMProviderError("LLM provider rate limit reached. Please retry shortly.")
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "): continue  # Includes OpenRouter SSE keepalive comments.
                        data = line[6:]
                        if data == "[DONE]": break
                        message = json.loads(data)
                        if error := message.get("error"):
                            logger.error("llm_stream_interrupted provider=openai code=%s type=%s", error.get("code"), error.get("metadata", {}).get("error_type"))
                            raise LLMProviderError(f"LLM stream interrupted: {error.get('message', 'provider error')}")
                        chunk = message.get("choices", [{}])[0].get("delta", {}).get("content")
                        if chunk: yield chunk
        except LLMProviderError:
            raise
        except httpx.TimeoutException as exc:
            logger.error("llm_timeout provider=openai error=%s", type(exc).__name__)
            raise LLMProviderError("LLM request timed out. Please retry.") from exc
        except httpx.HTTPStatusError as exc:
            logger.error("llm_http_error provider=openai status=%s", exc.response.status_code)
            raise LLMProviderError(f"LLM provider returned HTTP {exc.response.status_code}.") from exc
        except httpx.HTTPError as exc:
            logger.error("llm_connection_error provider=openai error=%s", type(exc).__name__)
            raise LLMProviderError("Could not connect to the LLM provider.") from exc
        except (json.JSONDecodeError, IndexError, KeyError) as exc:
            logger.error("llm_stream_parse_error provider=openai error=%s", type(exc).__name__)
            raise LLMProviderError("LLM stream returned an invalid or interrupted response.") from exc

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
