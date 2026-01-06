# FastAPI Enterprise Backend

This project is a FastAPI-based enterprise backend with PostgreSQL, Docker, and Alembic migrations.

## 🚀 Quickstart

1. Build and run with Docker:
   ```bash
   docker-compose up --build
   ```
2. Run the app
   ```bash
   uvicorn backend_app.main:app --reload
   ```
2. Access API at: [http://localhost:8000](http://localhost:8000)

3. Default DB credentials:
   - User: admin
   - Password: admin123
   - Database: fastapi_db

## 📂 Structure
- `app/api/v1` → Versioned API routes
- `app/core` → Config & security
- `app/db` → Database models & session
- `app/services` → Business logic
- `tests` → Unit tests
- `alembic` → Database migrations
