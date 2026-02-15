# Production Overview

This project is architected for production using a microservices-inspired structure located in the `services/` and `shared/` directories.

## Architecture
- **API Service (`services/api`)**: FastAPI backend serving the frontend.
- **Worker Service (`services/worker`)**: Background service for scheduled model training.
- **Shared Library (`shared/`)**: Common logic for ML models, data fetching, and configuration.

## Deployment Steps
1. **Infrastructure**: Setup **Supabase** (Postgres + Storage).
2. **Backend**: Deploy to **Render/Railway** using the root `render.yaml` or individual Dockerfiles.
3. **Frontend**: Deploy `frontend/` to **Vercel**.
4. **Secrets**: Inject variables as listed in `production_guide.md`.

## Key Features for Production
- **S3 Model Storage**: Models are saved to S3-compatible storage (Supabase) to persist across server restarts.
- **Postgres Registry**: Model metadata is stored in a real database for reliability.
- **Separation of Concerns**: Inference (API) and Training (Worker) can scale independently.
