from sqlalchemy.exc import IntegrityError
from app.application.interfaces.user_repository import IUserRepository
from app.presentation.schemas.user_schema import UserDeleteResponse


class DeleteUserUseCase:
    def __init__(self, repository: IUserRepository):
        self.repository = repository

    async def soft_delete(self, id) ->UserDeleteResponse:
        user = self.repository.get_by_id(id, is_deleted=False)
        if not user:
            return "user not found"
        try:
            deleted = self.repository.delete_user_and_return(id)
        except IntegrityError:
            raise ValueError("Username or Email already exists")

        return {"message":"User deleted successfully",
                "data":UserOut.model_validate(deleted_user, from_attributes=True)
                }

