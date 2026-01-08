
# app/core/settings.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Settings(BaseSettings):
    # Ignore unknown env keys; read .env; case-insensitive on env names
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False
    )

    app_name: str = "QMS Backend"
    app_env: str = "development"
    # This will map from env var DB_URL automatically
    db_url: str = "postgresql+asyncpg://admin:admin123@db:5432/qms"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"



def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)



settings = Settings()
