"""Application commands for identity management."""

from swen_identity.application.commands.change_password_command import (
    ChangePasswordCommand,
)
from swen_identity.application.commands.create_user_command import CreateUserCommand
from swen_identity.application.commands.delete_user_command import DeleteUserCommand
from swen_identity.application.commands.forgot_password_command import (
    ForgotPasswordCommand,
)
from swen_identity.application.commands.login_command import LoginCommand
from swen_identity.application.commands.register_command import RegisterCommand
from swen_identity.application.commands.reset_password_command import (
    ResetPasswordCommand,
)
from swen_identity.application.commands.update_user_role_command import (
    UpdateUserRoleCommand,
)

__all__ = [
    "ChangePasswordCommand",
    "CreateUserCommand",
    "DeleteUserCommand",
    "ForgotPasswordCommand",
    "LoginCommand",
    "RegisterCommand",
    "ResetPasswordCommand",
    "UpdateUserRoleCommand",
]
