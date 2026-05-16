"""Domain exceptions — used by services to signal errors without HTTP coupling."""


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str = "Resource", identifier: str = "") -> None:
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} '{identifier}' not found"
        super().__init__(detail)
        self.detail = detail


class ConflictError(Exception):
    """Raised when an operation would create an invalid or duplicate state."""

    def __init__(self, detail: str = "Conflict") -> None:
        super().__init__(detail)
        self.detail = detail
