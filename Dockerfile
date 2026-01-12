FROM python:3.11-slim

RUN pip install --no-cache-dir --upgrade pip
WORKDIR /app
#COPY . /app

# install project deps; optionally copy requirements first for better caching
#COPY requirements.txt .
#RUN pip install --no-cache-dir -r requirements.txt

# Install runtime & migration deps
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    "sqlalchemy[asyncio]" \
    asyncpg \
    psycopg2-binary \
    alembic \
    python-dotenv \
    pydantic \
    pydantic-settings\
    passlib\
    'pydantic[email]'

#ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1