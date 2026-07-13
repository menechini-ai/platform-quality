"""Gateway Secret authentication (Versus parity)."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config_loader import load_config

security = HTTPBearer(auto_error=False)


async def verify_gateway_secret(
    request: Request,
    x_gateway_secret: str | None = Header(None, alias="X-Gateway-Secret"),
    authorization: HTTPAuthorizationCredentials | None = Depends(security),
) -> bool:
    """
    Verify gateway secret for admin/agent endpoints.

    Versus parity: All admin endpoints (/api/admin/*, /api/agent/*) require
    the root-level gateway_secret in X-Gateway-Secret header.
    """
    try:
        config = load_config()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configuration not loaded",
        )

    expected = config.gateway_secret
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gateway secret not configured",
        )

    # Check header first, then Authorization Bearer
    provided = x_gateway_secret
    if not provided and authorization:
        provided = authorization.credentials

    if not provided or provided != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid gateway secret",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


def require_gateway_secret() -> Depends:
    """Dependency that requires valid gateway secret."""
    return Depends(verify_gateway_secret)


# Alias for common usage
gateway_auth = verify_gateway_secret
