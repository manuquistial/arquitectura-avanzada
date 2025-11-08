"""Session cache management using Redis."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from redis.exceptions import RedisError

from app.config import get_config
from app.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return aware UTC datetime."""
    return datetime.now(timezone.utc)


def _to_iso(dt: datetime) -> str:
    """Convert datetime to ISO string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _from_iso(value: str) -> datetime:
    """Parse ISO datetime string into aware datetime."""
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass
class SessionRecord:
    """Internal representation of a session."""

    session_id: str
    user_id: str
    email: str
    name: Optional[str]
    roles: list[str]
    permissions: list[str]
    created_at: datetime
    expires_at: datetime
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "roles": self.roles,
            "permissions": self.permissions,
            "created_at": _to_iso(self.created_at),
            "expires_at": _to_iso(self.expires_at),
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionRecord":
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            email=data["email"],
            name=data.get("name"),
            roles=list(data.get("roles", [])),
            permissions=list(data.get("permissions", [])),
            created_at=_from_iso(data["created_at"]),
            expires_at=_from_iso(data["expires_at"]),
            is_active=bool(data.get("is_active", True)),
        )

    def is_expired(self) -> bool:
        return self.expires_at <= _utc_now()


class SessionStoreError(RuntimeError):
    """Base error for session store operations."""


class SessionNotFound(SessionStoreError):
    """Raised when a session is not found."""


class RedisSessionStore:
    """Redis-backed session storage."""

    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = max(ttl_seconds, 60)
        self._namespace = "auth"

    def _session_key(self, session_id: str) -> str:
        return f"{self._namespace}:session:{session_id}"

    def _user_index_key(self, user_id: str) -> str:
        return f"{self._namespace}:user:{user_id}:sessions"

    async def create_session(self, payload: Dict[str, Any]) -> SessionRecord:
        session_id = payload.get("session_id") or str(uuid.uuid4())
        now = _utc_now()
        expires_at = now + timedelta(seconds=self.ttl_seconds)

        record = SessionRecord(
            session_id=session_id,
            user_id=payload["user_id"],
            email=payload["email"],
            name=payload.get("name"),
            roles=list(payload.get("roles", [])),
            permissions=list(payload.get("permissions", [])),
            created_at=now,
            expires_at=expires_at,
        )

        client = await get_redis_client()
        key = self._session_key(session_id)
        user_key = self._user_index_key(record.user_id)

        data = json.dumps(record.to_dict())

        try:
            async with client.pipeline(transaction=True) as pipe:
                pipe.set(key, data, ex=self.ttl_seconds)
                pipe.sadd(user_key, session_id)
                pipe.expire(user_key, self.ttl_seconds)
                await pipe.execute()
            logger.info("Session %s stored in Redis for user %s", session_id, record.user_id)
        except RedisError as exc:
            logger.exception("Failed to write session to Redis")
            raise SessionStoreError("Failed to store session in Redis") from exc

        return record

    async def get_session(self, session_id: str) -> SessionRecord:
        client = await get_redis_client()
        key = self._session_key(session_id)

        try:
            raw = await client.get(key)
        except RedisError as exc:
            logger.exception("Failed to fetch session from Redis")
            raise SessionStoreError("Failed to fetch session from Redis") from exc

        if raw is None:
            raise SessionNotFound(f"Session {session_id} not found")

        record = SessionRecord.from_dict(json.loads(raw))
        if record.is_expired():
            await self.delete_session(session_id)
            raise SessionNotFound(f"Session {session_id} expired")

        return record

    async def delete_session(self, session_id: str) -> None:
        client = await get_redis_client()

        key = self._session_key(session_id)

        try:
            raw = await client.get(key)
        except RedisError as exc:
            logger.exception("Failed to fetch session for deletion from Redis")
            raise SessionStoreError("Failed to delete session from Redis") from exc

        if raw is None:
            raise SessionNotFound(f"Session {session_id} not found")

        record = SessionRecord.from_dict(json.loads(raw))

        try:
            async with client.pipeline(transaction=True) as pipe:
                pipe.delete(key)
                pipe.srem(self._user_index_key(record.user_id), session_id)
                await pipe.execute()
        except RedisError as exc:
            logger.exception("Failed to delete session from Redis")
            raise SessionStoreError("Failed to delete session from Redis") from exc

    async def refresh_session(self, session_id: str) -> SessionRecord:
        record = await self.get_session(session_id)
        record.expires_at = _utc_now() + timedelta(seconds=self.ttl_seconds)

        client = await get_redis_client()
        key = self._session_key(session_id)
        user_key = self._user_index_key(record.user_id)

        try:
            async with client.pipeline(transaction=True) as pipe:
                pipe.set(key, json.dumps(record.to_dict()), ex=self.ttl_seconds)
                pipe.expire(user_key, self.ttl_seconds)
                await pipe.execute()
        except RedisError as exc:
            logger.exception("Failed to refresh session in Redis")
            raise SessionStoreError("Failed to refresh session in Redis") from exc

        return record


class InMemorySessionStore:
    """Fallback in-memory session store (tests/dev)."""

    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = max(ttl_seconds, 60)
        self._sessions: Dict[str, SessionRecord] = {}

    async def create_session(self, payload: Dict[str, Any]) -> SessionRecord:
        session_id = payload.get("session_id") or str(uuid.uuid4())
        now = _utc_now()
        expires_at = now + timedelta(seconds=self.ttl_seconds)
        record = SessionRecord(
            session_id=session_id,
            user_id=payload["user_id"],
            email=payload["email"],
            name=payload.get("name"),
            roles=list(payload.get("roles", [])),
            permissions=list(payload.get("permissions", [])),
            created_at=now,
            expires_at=expires_at,
        )
        self._sessions[session_id] = record
        return record

    async def get_session(self, session_id: str) -> SessionRecord:
        record = self._sessions.get(session_id)
        if not record or record.is_expired():
            self._sessions.pop(session_id, None)
            raise SessionNotFound(f"Session {session_id} not found")
        return record

    async def delete_session(self, session_id: str) -> None:
        if session_id not in self._sessions:
            raise SessionNotFound(f"Session {session_id} not found")
        self._sessions.pop(session_id, None)

    async def refresh_session(self, session_id: str) -> SessionRecord:
        record = await self.get_session(session_id)
        record.expires_at = _utc_now() + timedelta(seconds=self.ttl_seconds)
        self._sessions[session_id] = record
        return record


def _build_session_store():
    config = get_config()
    ttl_seconds = max(config.session_ttl_minutes * 60, 60)

    if config.redis_enabled:
        logger.info("Using RedisSessionStore for session management")
        return RedisSessionStore(ttl_seconds)

    logger.warning("Redis disabled; using in-memory session store")
    return InMemorySessionStore(ttl_seconds)


session_store = _build_session_store()


