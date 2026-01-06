.PHONY: build up down logs bash migrate revision reset check-db

build:
\tdocker-compose build

up:
\tdocker-compose up -d

down:
\tdocker-compose down

logs:
\tdocker-compose logs -f

bash:
\tdocker-compose exec web bash

revision:
\tdocker-compose exec web alembic revision --autogenerate -m "$(m)"

migrate:
\tdocker-compose exec web alembic upgrade head

check-db:
\tdocker exec -it postgres_db psql -U $(DB_USER) -d $(DB_NAME) -c "\dt"

reset:
\tdocker-compose down -v && docker-compose up --build -d && docker-compose exec web alembic upgrade head