# Production Overview

This project is architected for production using a microservices-inspired structure located in the `services/` and `shared/` directories.

## Architecture
- **API Service (`services/api`)**: FastAPI backend serving inference and metrics.
- **Local Training Utility (`local_train.py`)**: Powerful local script to train models and push them to Supabase.
- **Shared Library (`shared/`)**: Common logic for ML models, data fetching, and registry.

## Deployment Steps
1. **Infrastructure**: Setup **Supabase** (Postgres + Storage).
2. **Backend**: Deploy `services/api` to **Render**.
3. **Frontend**: Deploy `frontend/` to **Vercel**.
4. **Training**: Run `python local_train.py` from your own machine to initialize/update models.

## Key Features
- **Local-to-Cloud Training**: Bypass server memory limits (512MB) by training locally and pushing to S3.
- **Persistent Model Registry**: Models are indexed in Postgres for fast loading by the API.
- **Optimized for Production**: Separated inference and training for maximum stability.
