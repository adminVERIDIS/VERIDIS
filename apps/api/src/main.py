from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import boto3
import httpx
from fastapi import FastAPI
from redis.asyncio import from_url as redis_from_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@dataclass(frozen=True)
class Settings:
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    database_url: str | None = os.getenv("DATABASE_URL")
    redis_url: str | None = os.getenv("REDIS_URL")
    s3_backup_bucket: str | None = os.getenv("S3_BACKUP_BUCKET")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")


settings = Settings()

app = FastAPI(
    title="VERIDIS API",
    version=settings.app_version,
    docs_url="/docs" if os.getenv("ENABLE_API_DOCS") == "true" else None,
    redoc_url=None,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check simple pour load balancers."""

    return {
        "status": "ok",
        "service": "veridis-api",
        "version": settings.app_version,
    }


@app.get("/health/detailed")
async def health_detailed() -> dict[str, Any]:
    """Health check detaille avec dependances externes."""

    checks = {
        "database": await _safe_check(check_database),
        "redis": await _safe_check(check_redis),
        "s3": await _safe_check(check_s3),
        "openai": await _safe_check(check_openai),
    }
    status = "ok" if all(check["status"] in {"ok", "skipped"} for check in checks.values()) else "degraded"
    return {
        "status": status,
        "service": "veridis-api",
        "version": settings.app_version,
        "checks": checks,
    }


async def _safe_check(check: Callable[[], Awaitable[dict[str, str]]]) -> dict[str, str]:
    try:
        return await asyncio.wait_for(check(), timeout=5)
    except TimeoutError:
        return {"status": "degraded", "message": "timeout"}
    except Exception as exc:
        return {"status": "degraded", "message": str(exc)[:240]}


async def check_database() -> dict[str, str]:
    if not settings.database_url:
        return {"status": "skipped", "message": "DATABASE_URL not configured"}

    url = _to_async_database_url(settings.database_url)
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1"))
        return {"status": "ok"}
    finally:
        await engine.dispose()


async def check_redis() -> dict[str, str]:
    if not settings.redis_url:
        return {"status": "skipped", "message": "REDIS_URL not configured"}

    client = redis_from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
    try:
        await client.ping()
        return {"status": "ok"}
    finally:
        await client.aclose()


async def check_s3() -> dict[str, str]:
    if not settings.s3_backup_bucket:
        return {"status": "skipped", "message": "S3_BACKUP_BUCKET not configured"}

    bucket_name = settings.s3_backup_bucket.removeprefix("s3://").strip("/")

    def head_bucket() -> None:
        boto3.client("s3").head_bucket(Bucket=bucket_name)

    await asyncio.to_thread(head_bucket)
    return {"status": "ok"}


async def check_openai() -> dict[str, str]:
    if not settings.openai_api_key:
        return {"status": "skipped", "message": "OPENAI_API_KEY not configured"}

    async with httpx.AsyncClient(timeout=3) as client:
        response = await client.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        )
    if 200 <= response.status_code < 300:
        return {"status": "ok"}
    return {"status": "degraded", "message": f"openai status {response.status_code}"}


def _to_async_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url
