class DomainError(Exception):
    """Base domain error."""


class OwnershipError(DomainError):
    """Raised when an entity does not belong to the specified parent."""
