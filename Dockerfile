FROM python:3.11-slim

RUN pip install --no-cache-dir --upgrade pip
WORKDIR /app
COPY . /app

# Install runtime & migration deps
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    "sqlalchemy[asyncio]" \
    asyncpg \
    psycopg2-binary \
    alembic \
    python-dotenv \
    pydantic \
    pydantic-settings\
    passlib\
    'pydantic[email]'

ENV PYTHONPATH=/app
