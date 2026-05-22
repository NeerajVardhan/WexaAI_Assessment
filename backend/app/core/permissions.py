from enum import StrEnum

from app.core.exceptions import PermissionDenied


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


ROLE_ORDER = {
    Role.OWNER: 4,
    Role.ADMIN: 3,
    Role.ANALYST: 2,
    Role.VIEWER: 1,
}


def assert_role(user_role: str, minimum: Role) -> None:
    role = Role(user_role)
    if ROLE_ORDER[role] < ROLE_ORDER[minimum]:
        raise PermissionDenied(f"{minimum.value} role or higher is required")

