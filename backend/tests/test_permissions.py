import pytest

from app.core.exceptions import PermissionDenied
from app.core.permissions import Role, assert_role


def test_owner_satisfies_admin_guard() -> None:
    assert_role(Role.OWNER.value, Role.ADMIN)


def test_viewer_fails_analyst_guard() -> None:
    with pytest.raises(PermissionDenied):
        assert_role(Role.VIEWER.value, Role.ANALYST)
