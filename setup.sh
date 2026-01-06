#!/bin/bash

# Project root
PROJECT_NAME="backend"
mkdir -p $PROJECT_NAME
cd $PROJECT_NAME

# Backend app directories
mkdir -p backend_app/api/v1
mkdir -p backend_app/core
mkdir -p backend_app/db/models
mkdir -p backend_app/services
touch backend_app/__init__.py backend_app/main.py
touch backend_app/api/v1/__init__.py backend_app/api/v1/users.py backend_app/api/v1/auth.py
touch backend_app/core/__init__.py backend_app/core/config.py backend_app/core/security.py
touch backend_app/db/__init__.py backend_app/db/base.py backend_app/db/session.py
touch backend_app/db/models/__init__.py backend_app/db/models/user.py
touch backend_app/services/__init__.py backend_app/services/user_service.py

# Tests
mkdir -p tests
touch tests/__init__.py tests/test_users.py

# requirements.txt
cat <<EOL > requirements.txt
fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
alembic
python-dotenv
EOL

# Dockerfile
cat <<EOL > Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./backend_app ./backend_app
COPY ./alembic ./alembic
COPY alembic.ini .

CMD ["uvicorn", "backend_app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EOL

# docker-compose.yml
cat <<EOL > docker-compose.yml
version: "3.9"
services:
  db:
    image: postgres:15
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: admin123
      POSTGRES_DB: fastapi_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  web:
    build: .
    container_name: fastapi_app
    restart: always
    depends_on:
      - db
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgres://admin:admin123@db:5432/fastapi_db

volumes:
  postgres_data:
EOL

# Alembic setup
mkdir -p alembic/versions

cat <<EOL > alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = postgres://admin:admin123@localhost:5432/fastapi_db
EOL

cat <<EOL > alembic/env.py
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend_app.db import base
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config
fileConfig(config.config_file_name)
target_metadata = base.Base.metadata

def run_migrations_offline():
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
EOL

# Base model
cat <<EOL > backend_app/db/base.py
from sqlalchemy.orm import declarative_base

Base = declarative_base()
EOL

# User model
cat <<EOL > backend_app/db/models/user.py
from sqlalchemy import Column, Integer, String
from backend_app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
EOL

echo "✅ Enterprise FastAPI scaffold created with backend_app namespace!"