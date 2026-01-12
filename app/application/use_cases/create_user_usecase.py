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
        username = payload.Username.strip()
        email = payload.Email.strip().lower()
        admin = payload.Admin or False

# Pre-check duplicates for nicer messages (DB unique will also protect)
        if await self.repo.get_by_username(username):
            raise ValueError("Username already exists")
        if await self.repo.get_by_email(email):
            raise ValueError("Email already exists")

        hashed = get_password_hash(payload.Password)

        model = UserModel(
            Username=username,
            Email=email,
            hashed_password=hashed,
            Admin=admin,
            Active=True,
            Approved=False,
            Locked=False,
            Department=payload.Department,
            Unit=payload.Unit,
            FirstName=payload.FirstName,
            MiddleName=payload.MiddleName,
            LastName=payload.LastName,
            RssToken=payload.RssToken,
        )

        try:
            created = await self.repo.create(model)
        except IntegrityError:
            raise ValueError("Username or Email already exists")

        return UserSummary.model_validate(created)