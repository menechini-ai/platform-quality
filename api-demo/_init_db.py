"""Initialize DB tables."""
import asyncio
from app.core.db import engine, Base
from app.core.models.health import HealthSnapshot, Slo  # noqa: F401
from app.core.models.incident import Incident  # noqa: F401
from app.core.models.rca import RcaReport  # noqa: F401
from app.core.models.maturity import MaturityAssessment  # noqa: F401
from app.core.models.self_healing import Runbook, AutoHealAction  # noqa: F401
from app.core.models.report import Report  # noqa: F401
from app.core.config import settings


async def init():
    print(f"DB URL: {settings.DATABASE_URL}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("tables created")


asyncio.run(init())
