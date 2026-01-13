"""User domain exceptions.

Custom exceptions for the user domain, used for validation
and business rule violations.
"""


class InvalidEmailError(ValueError):
    """
    Raised when email format is invalid.

    This exception is raised during Email value object creation
    when the provided string doesn't match expected email format.

    Attributes
    ----------
    message
        Error description
    """

    def __init__(self, message: str) -> None:
        """
        Initialize the exception.

        Parameters
        ----------
        message
            Error message describing the validation failure
        """
        super().__init__(message)


class EmailAlreadyExistsError(Exception):
    """Email already registered."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"Email already registered: {email}")


class UserNotFoundError(Exception):
    """User not found."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")


class CannotDeleteSelfError(Exception):
    """Cannot delete your own account."""

    def __init__(self) -> None:
        super().__init__("Cannot delete your own account")


class CannotDemoteSelfError(Exception):
    """Cannot demote yourself from admin."""

    def __init__(self) -> None:
        super().__init__("Cannot demote yourself from admin")
