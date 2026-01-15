from sqlalchemy.exc import IntegrityError
from app.application.interfaces.user_repository import IUserRepository
from app.core.settings import get_password_hash
from app.presentation.schemas.user_schema import UserCreate, UserOut, UserSummary
from app.infrastructure.models.user_model import User as UserModel

class CreateUserUseCase:
    def __init__(self, repo: IUserRepository) -> None:
        self.repo = repo

    async def execute(self, payload: UserCreate) -> UserSummary:
        # Optional normalization
        username = payload.username.strip()
        email = payload.email.strip().lower()
        admin = payload.admin or False

# Pre-check duplicates for nicer messages (DB unique will also protect)
        if await self.repo.get_by_username(username):
            raise ValueError("Username already exists")
        if await self.repo.get_by_email(email):
            raise ValueError("Email already exists")

        hashed = get_password_hash(payload.password)

        model = UserModel(
            username=username,
            email=email,
            hashed_password=hashed,
            admin=admin,
            active=True,
            approved=False,
            locked=False,
            department=payload.department,
            unit=payload.unit,
            first_name=payload.first_name,
            middle_name=payload.middle_name,
            last_name=payload.last_name,
            rss_token=payload.rss_token,
        )

        try:
            created = await self.repo.create(model)
        except IntegrityError:
            raise ValueError("Username or Email already exists")

        return UserSummary.model_validate(created)