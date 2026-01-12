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
    """
    Raised when attempting to register with an existing email.

    This exception is raised during user creation when the email
    is already associated with another user account.

    Attributes
    ----------
    email
        The email that already exists
    """

    def __init__(self, email: str) -> None:
        """
        Initialize the exception.

        Parameters
        ----------
        email
            The email address that already exists
        """
        self.email = email
        super().__init__(f"Email already registered: {email}")

