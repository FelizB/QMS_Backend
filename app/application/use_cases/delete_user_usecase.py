from fastapi import HTTPException, status

from app.application.interfaces.user_repository import IUserRepository
from app.presentation.schemas.user_schema import UserDeleteResponse, UserOut


class DeleteUserUseCase:
    def __init__(self, repository: IUserRepository):
        self.repository = repository

    async def soft_delete(self, id: int) -> UserDeleteResponse:
        # soft delete
        deleted = await self.repository.delete_user_and_return(id)

        if not deleted:
            # Either already deleted or race condition
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not Found or already deleted")
        return UserDeleteResponse(
            message="User deleted successfully",
            data=UserOut.model_validate(deleted, from_attributes=True),
        )
