"""Authentication stub for future dashboard access control."""

from __future__ import annotations

from fastapi import Depends

from githubbench_delta.dashboard.schemas import Principal


async def get_current_principal() -> Principal:
    """Return an anonymous principal until real auth is wired."""

    return Principal()


# Convenience alias for route dependencies.
RequirePrincipal = Depends(get_current_principal)
