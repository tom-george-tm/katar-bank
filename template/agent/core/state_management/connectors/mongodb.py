"""MongoDB session service - ADK BaseSessionService backed by Motor."""

from __future__ import annotations

import asyncio
import copy
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from agent.core.config import settings
from google.adk.errors.already_exists_error import AlreadyExistsError  # type: ignore[import-not-found]
from google.adk.events.event import Event  # type: ignore[import-not-found]
from google.adk.sessions.base_session_service import (  # type: ignore[import-not-found]
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session  # type: ignore[import-not-found]
from google.adk.sessions.state import State  # type: ignore[import-not-found]
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore[import-not-found]


def _extract_state_delta(state: Optional[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Split state into app, user, and session scopes using ADK prefixes."""
    deltas = {"app": {}, "user": {}, "session": {}}
    if not state:
        return deltas

    for key, value in state.items():
        if key.startswith(State.APP_PREFIX):
            deltas["app"][key.removeprefix(State.APP_PREFIX)] = value
        elif key.startswith(State.USER_PREFIX):
            deltas["user"][key.removeprefix(State.USER_PREFIX)] = value
        elif not key.startswith(State.TEMP_PREFIX):
            deltas["session"][key] = value
    return deltas


def _merge_state(
    app_state: dict[str, Any],
    user_state: dict[str, Any],
    session_state: dict[str, Any],
) -> dict[str, Any]:
    """Rebuild the ADK-visible merged state for a session."""
    merged_state = copy.deepcopy(session_state)
    for key, value in app_state.items():
        merged_state[State.APP_PREFIX + key] = value
    for key, value in user_state.items():
        merged_state[State.USER_PREFIX + key] = value
    return merged_state


def _to_timestamp(value: Any) -> float:
    """Convert a stored datetime value to the ADK float timestamp format."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()
    return 0.0


def _to_datetime(timestamp: float) -> datetime:
    """Convert ADK float timestamps to timezone-aware datetimes."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


class MongoDBSessionService(BaseSessionService):
    """Session service backed by MongoDB collections."""

    def __init__(self, uri: str, database: str, sessions_collection: str = "sessions"):
        self._client = AsyncIOMotorClient(uri)
        self._db = self._client[database]
        self._sessions = self._db[sessions_collection]
        self._events = self._db[f"{sessions_collection}_events"]
        self._app_state = self._db[f"{sessions_collection}_app_state"]
        self._user_state = self._db[f"{sessions_collection}_user_state"]
        self._indexes_ready = False
        self._index_lock = asyncio.Lock()

    async def _ensure_indexes(self) -> None:
        if self._indexes_ready:
            return

        async with self._index_lock:
            if self._indexes_ready:
                return

            await self._sessions.create_index(
                [("app_name", 1), ("user_id", 1), ("updated_at", -1)]
            )
            await self._events.create_index(
                [("app_name", 1), ("user_id", 1), ("session_id", 1), ("timestamp", 1)]
            )
            await self._app_state.create_index("app_name", unique=True)
            await self._user_state.create_index([("app_name", 1), ("user_id", 1)], unique=True)
            self._indexes_ready = True

    async def _get_app_state(self, app_name: str) -> dict[str, Any]:
        doc = await self._app_state.find_one({"app_name": app_name}, {"_id": 0, "state": 1})
        return (doc or {}).get("state", {})

    async def _get_user_state(self, app_name: str, user_id: str) -> dict[str, Any]:
        doc = await self._user_state.find_one(
            {"app_name": app_name, "user_id": user_id},
            {"_id": 0, "state": 1},
        )
        return (doc or {}).get("state", {})

    async def _apply_state_delta(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        state_delta: dict[str, Any],
    ) -> None:
        deltas = _extract_state_delta(state_delta)
        app_state_delta = deltas["app"]
        user_state_delta = deltas["user"]
        session_state_delta = deltas["session"]

        if app_state_delta:
            await self._app_state.update_one(
                {"app_name": app_name},
                {
                    "$set": {
                        **{f"state.{key}": value for key, value in app_state_delta.items()},
                        "app_name": app_name,
                    }
                },
                upsert=True,
            )
        if user_state_delta:
            await self._user_state.update_one(
                {"app_name": app_name, "user_id": user_id},
                {
                    "$set": {
                        **{f"state.{key}": value for key, value in user_state_delta.items()},
                        "app_name": app_name,
                        "user_id": user_id,
                    }
                },
                upsert=True,
            )
        if session_state_delta:
            await self._sessions.update_one(
                {"_id": session_id, "app_name": app_name, "user_id": user_id},
                {"$set": {f"state.{key}": value for key, value in session_state_delta.items()}},
            )

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        await self._ensure_indexes()

        session_id = session_id or str(uuid4())
        existing = await self._sessions.find_one({"_id": session_id}, {"_id": 1})
        if existing is not None:
            raise AlreadyExistsError(f"Session with id {session_id} already exists.")

        deltas = _extract_state_delta(state)
        app_state = await self._get_app_state(app_name)
        user_state = await self._get_user_state(app_name, user_id)

        merged_app_state = app_state | deltas["app"]
        merged_user_state = user_state | deltas["user"]
        session_state = deltas["session"]
        now = datetime.now(timezone.utc)

        await self._apply_state_delta(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            state_delta=state or {},
        )
        await self._sessions.insert_one(
            {
                "_id": session_id,
                "app_name": app_name,
                "user_id": user_id,
                "state": session_state,
                "created_at": now,
                "updated_at": now,
            }
        )

        return Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=_merge_state(merged_app_state, merged_user_state, session_state),
            last_update_time=now.timestamp(),
        )

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        await self._ensure_indexes()

        session_doc = await self._sessions.find_one(
            {"_id": session_id, "app_name": app_name, "user_id": user_id}
        )
        if session_doc is None:
            return None

        app_state = await self._get_app_state(app_name)
        user_state = await self._get_user_state(app_name, user_id)

        query: dict[str, Any] = {
            "app_name": app_name,
            "user_id": user_id,
            "session_id": session_id,
        }
        if config and config.after_timestamp:
            query["timestamp"] = {"$gte": config.after_timestamp}

        cursor = self._events.find(query).sort("timestamp", -1)
        if config and config.num_recent_events:
            cursor = cursor.limit(config.num_recent_events)
            event_docs = await cursor.to_list(length=config.num_recent_events)
            event_docs.reverse()
        else:
            cursor = self._events.find(query).sort("timestamp", 1)
            event_docs = await cursor.to_list(length=None)

        events = [Event.model_validate(doc["payload"]) for doc in event_docs]
        return Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=_merge_state(app_state, user_state, session_doc.get("state", {})),
            events=events,
            last_update_time=_to_timestamp(session_doc.get("updated_at")),
        )

    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        await self._ensure_indexes()

        query: dict[str, Any] = {"app_name": app_name}
        if user_id is not None:
            query["user_id"] = user_id

        app_state = await self._get_app_state(app_name)
        sessions_cursor = self._sessions.find(query).sort("updated_at", -1)
        session_docs = await sessions_cursor.to_list(length=None)

        user_states_map: dict[str, dict[str, Any]] = {}
        if user_id is not None:
            user_states_map[user_id] = await self._get_user_state(app_name, user_id)
        else:
            user_docs = await self._user_state.find({"app_name": app_name}).to_list(length=None)
            user_states_map = {
                doc["user_id"]: doc.get("state", {})
                for doc in user_docs
            }

        sessions = [
            Session(
                app_name=doc["app_name"],
                user_id=doc["user_id"],
                id=doc["_id"],
                state=_merge_state(
                    app_state,
                    user_states_map.get(doc["user_id"], {}),
                    doc.get("state", {}),
                ),
                last_update_time=_to_timestamp(doc.get("updated_at")),
            )
            for doc in session_docs
        ]
        return ListSessionsResponse(sessions=sessions)

    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        await self._ensure_indexes()

        await self._events.delete_many(
            {"app_name": app_name, "user_id": user_id, "session_id": session_id}
        )
        await self._sessions.delete_one(
            {"_id": session_id, "app_name": app_name, "user_id": user_id}
        )

    async def append_event(self, session: Session, event: Event) -> Event:
        await self._ensure_indexes()
        if event.partial:
            return event

        event = self._trim_temp_delta_state(event)
        event.id = event.id or str(uuid4())

        session_doc = await self._sessions.find_one(
            {"_id": session.id, "app_name": session.app_name, "user_id": session.user_id}
        )
        if session_doc is None:
            raise ValueError(f"Session {session.id!r} does not exist.")

        stored_last_update = _to_timestamp(session_doc.get("updated_at"))
        if stored_last_update > session.last_update_time:
            raise ValueError(
                "The provided session is stale. Reload the session before appending new events."
            )

        if event.actions and event.actions.state_delta:
            await self._apply_state_delta(
                app_name=session.app_name,
                user_id=session.user_id,
                session_id=session.id,
                state_delta=event.actions.state_delta,
            )

        await self._sessions.update_one(
            {"_id": session.id, "app_name": session.app_name, "user_id": session.user_id},
            {"$set": {"updated_at": _to_datetime(event.timestamp)}},
        )
        await self._events.insert_one(
            {
                "_id": event.id,
                "app_name": session.app_name,
                "user_id": session.user_id,
                "session_id": session.id,
                "timestamp": event.timestamp,
                "payload": event.model_dump(mode="json", exclude_none=True),
            }
        )

        session.last_update_time = event.timestamp
        await super().append_event(session=session, event=event)
        return event


def create_mongodb_session_service():
    """Create MongoDB-backed session service using Motor."""
    uri = (settings.MONGODB_URI or "").strip()
    if not uri:
        raise ValueError(
            "MONGODB_URI must be set when SESSION_SERVICE_BACKEND=mongodb."
        )
    database = (settings.MONGODB_DATABASE or "").strip()
    if not database:
        raise ValueError(
            "MONGODB_DATABASE must be set when SESSION_SERVICE_BACKEND=mongodb."
        )
    return MongoDBSessionService(
        uri=uri,
        database=database,
        sessions_collection=settings.MONGODB_SESSIONS_COLLECTION or "sessions",
    )
