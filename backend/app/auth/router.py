"""Authentication routes: login, logout (token revocation), and current user."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.rate_limit import LoginRateLimiter
from app.auth.schemas import LoginRequest, TokenResponse, UserInfo
from app.auth.service import UserService
from app.core.config import settings
from app.core.db import get_db
from app.core.models.user import RevokedToken

security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/auth", tags=["auth"])

_login_limiter = LoginRateLimiter(
    max_attempts=settings.AUTH_RATE_LIMIT,
    window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    if not _login_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )

    user = await UserService.authenticate(db, body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user.username,
        "role": user.role,
        "type": "access",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": expire,
        "jti": uuid4().hex,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    if credentials is None:
        return {"detail": "ok"}
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
    except JWTError:
        return {"detail": "ok"}
    jti = payload.get("jti")
    if jti:
        db.add(
            RevokedToken(
                jti=jti,
                expires_at=datetime.fromtimestamp(payload.get("exp", 0), tz=UTC),
            )
        )
        await db.commit()
    return {"detail": "ok"}


@router.get("/me", response_model=UserInfo)
async def me(current_user: UserInfo = Depends(get_current_user)):
    return current_user
