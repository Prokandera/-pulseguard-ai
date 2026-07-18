# Backend

Run from this directory with `uvicorn app.main:app --reload`.

For real local OpenRouter streaming, copy `.env.example` to `.env` and set only `LLM_API_KEY` to your own key. The `.env` file is ignored by Git. The example selects `LLM_PROVIDER=openai`, `LLM_BASE_URL=https://openrouter.ai/api/v1`, and `LLM_MODEL=openrouter/free`. If the key is absent, the backend reports a clear streaming configuration error; use `LLM_PROVIDER=mock` for a credential-free demo.
