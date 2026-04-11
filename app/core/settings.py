from datetime import timedelta
from dotenv import load_dotenv
from passlib.context import CryptContext
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Settings(BaseSettings):
    # Ignore unknown env keys; read .env; case-insensitive on env names
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_prefix="QMS_",
        case_sensitive=False,
    )

    app_name: str = "QMS Backend"
    app_env: str = "development"
    # This will map from env var DB_URL automatically
    db_url: str = "postgresql+asyncpg://admin:admin123@db:5432/qms"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Auth
    ENFORCE_AUTH: bool = True  # flip to True to require auth globally on /api/v1/*
    JWT_SECRET_KEY: str = "CHANGE_ME_32+_CHARS"  # Use a long random value in prod
    JWT_REFRESH_SECRET_KEY: str = "CHANGE_ME_REFRESH_32+_CHARS"
    JWT_ALGORITHM: str = "HS256"
    JWT_ISS: str = "https://qms.example.com"
    JWT_AUD: str = "https://api.qms.example.com"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_LEEWAY_SECONDS: int = 60

    REFRESH_COOKIE_NAME: str = "refresh_token"
    REFRESH_COOKIE_SECURE: bool = True
    REFRESH_COOKIE_HTTPONLY: bool = True
    REFRESH_COOKIE_SAMESITE: str = "strict"

    # File upload
    FILES_STORAGE_BACKEND: str = "local"  # or "s3"
    FILES_LOCAL_ROOT: str = "/data/uploads"  # mount a Docker volume here
    MAX_UPLOAD_MB: int = 20
    ALLOWED_MIME: list[str] = [
        "application/pdf", "image/png", "image/jpeg",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/json", "text/csv"
    ]


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


settings = Settings()

ACCESS_TTL = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
REFRESH_TTL = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
