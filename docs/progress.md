# Development progress

## Core local application

- [x] Shared wearable sensor simulator and WebSocket feed
- [x] Isolation Forest anomaly pipeline with controlled demo trigger
- [x] SQLite anomaly history and REST retrieval
- [x] Mock and OpenAI-compatible incremental insight streaming
- [x] React dashboard, bounded charts, alert feed, and reconnecting socket hook
- [x] Local backend tests and frontend production build

## AWS Readiness

- [x] Environment-based configuration
- [x] Repository abstraction
- [x] SQLite repository
- [x] DynamoDB repository (optional, requires AWS configuration)
- [x] LLM provider abstraction
- [x] Mock LLM provider
- [x] OpenAI-compatible provider
- [x] Bedrock streaming provider (optional future AWS-native provider)
- [x] Initial AWS LLM configuration: OpenAI-compatible provider via Secrets Manager injection
- [x] Local OpenRouter OpenAI-compatible streaming configuration and safe provider error handling
- [x] ECS-compatible Dockerfile
- [x] Health endpoint
- [x] Readiness endpoint
- [x] Graceful shutdown
- [x] stdout logging
- [x] Configurable CORS
- [x] Configurable frontend API URL
- [x] Configurable WebSocket URL
- [x] Same-origin CloudFront frontend configuration
- [x] Dynamic REST API URL
- [x] Dynamic WebSocket URL
- [x] HTTPS to WSS automatic selection
- [x] AWS deployment architecture documentation

AWS infrastructure has **not** been created or deployed.
