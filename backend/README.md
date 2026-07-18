# Backend

Run from this directory with `uvicorn app.main:app --reload`. Copy `.env.example` to `.env` if you want to adjust simulator intervals, cooldown, or an OpenAI-compatible streaming provider. Without `LLM_API_KEY`, the intentionally delayed mock provider is selected.
