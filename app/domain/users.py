from dataclasses import dataclass
from datetime import datetime
from typing import Optional

class UserLockedError(Exception): ...
class ApprovalRequiredError(Exception): ...

@dataclass
class User:
    id: Optional[int]
    Username: str
    Email: str
    Department: str
    Unit: str
    FirstName: str
    MiddleName: str
    LastName: str
    RssToken: Optional[str]
    Admin: bool
    Active: bool
    Approved: bool
    Locked: bool
    created_at: datetime
    updated_at: datetime

    def full_name(self) -> str:
        mid = f" {self.MiddleName}" if self.MiddleName else ""
        return f"{self.FirstName}{mid} {self.LastName}"

    def lock(self) -> None:
        self.Locked = True
        self.Active = False

    def unlock(self) -> None:
        # policy: unlock requires approval
        if not self.Approved:
            raise ApprovalRequiredError("Cannot unlock a user who is not approved.")
        self.Locked = False

    def activate(self) -> None:
        if self.Locked:
            raise UserLockedError("Cannot activate a locked user.")
        self.Active = True

    def deactivate(self) -> None:
        self.Active = False

    def approve(self) -> None:
        self.Approved = True
