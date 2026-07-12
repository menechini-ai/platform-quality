"""Authentication service: user lookup, password verification, and token revocation."""

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.user import RevokedToken, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Database-backed user operations used by the auth routes."""

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> User | None:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    @staticmethod
    async def authenticate(db: AsyncSession, username: str, password: str) -> User | None:
        user = await UserService.get_by_username(db, username)
        if user is None or not user.is_active:
            return None
        if not UserService.verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    async def create_user(
        db: AsyncSession, username: str, password: str, role: str = "admin"
    ) -> User:
        user = User(username=username, password_hash=pwd_context.hash(password), role=role)
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def is_revoked(db: AsyncSession, jti: str | None) -> bool:
        if not jti:
            return False
        result = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti))
        return result.scalar_one_or_none() is not None
