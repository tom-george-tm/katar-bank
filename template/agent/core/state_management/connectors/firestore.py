# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Firestore session service - ADK BaseSessionService using Google Cloud Firestore."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.genai.types import Content, GroundingMetadata
from typing_extensions import override

logger = logging.getLogger("google_adk." + __name__)
logger.setLevel(logging.INFO)

SESSIONS_COLLECTION = "adk_sessions"
EVENTS_SUBCOLLECTION = "events"


class FirestoreSessionService(BaseSessionService):
    """Session service backed by Firestore. Use for production with FIRESTORE_PROJECT / FIRESTORE_DATABASE."""

    def __init__(self, project: Optional[str] = None, database: Optional[str] = None):
        self._db = firestore.Client(project=project, database=database)

    @override
    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        def _create():
            session_data = {
                "app_name": app_name,
                "user_id": user_id,
                "state": state or {},
                "createTime": firestore.SERVER_TIMESTAMP,
                "updateTime": firestore.SERVER_TIMESTAMP,
            }
            _, doc_ref = self._db.collection(SESSIONS_COLLECTION).add(session_data)
            doc = doc_ref.get()
            doc_dict = doc.to_dict()
            return Session(
                app_name=doc_dict["app_name"],
                user_id=doc_dict["user_id"],
                id=doc.id,
                state=doc_dict.get("state", {}),
                last_update_time=doc_dict["updateTime"].timestamp(),
            )

        return await asyncio.to_thread(_create)

    @override
    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        def _get():
            session_ref = self._db.collection(SESSIONS_COLLECTION).document(session_id)
            session_doc = session_ref.get()
            if not session_doc.exists:
                return None
            session_dict = session_doc.to_dict()
            if (
                session_dict.get("app_name") != app_name
                or session_dict.get("user_id") != user_id
            ):
                return None
            update_timestamp = session_dict["updateTime"].timestamp()
            session = Session(
                app_name=session_dict["app_name"],
                user_id=session_dict["user_id"],
                id=session_doc.id,
                state=session_dict.get("state", {}),
                last_update_time=update_timestamp,
            )
            events_ref = session_ref.collection(EVENTS_SUBCOLLECTION)
            query = events_ref
            if config and config.num_recent_events:
                query = query.order_by(
                    "timestamp", direction=firestore.Query.DESCENDING
                ).limit(config.num_recent_events)
                event_docs = list(query.stream())
                events_list = [_doc_to_event(d) for d in event_docs]
                events_list.reverse()
                session.events = events_list
            else:
                if config and config.after_timestamp:
                    after_dt = datetime.fromtimestamp(
                        config.after_timestamp, tz=timezone.utc
                    )
                    query = query.where(filter=FieldFilter("timestamp", ">", after_dt))
                query = query.order_by("timestamp", direction=firestore.Query.ASCENDING)
                session.events = [_doc_to_event(d) for d in query.stream()]
            return session

        return await asyncio.to_thread(_get)

    @override
    async def list_sessions(
        self, *, app_name: str, user_id: str
    ) -> ListSessionsResponse:
        def _list():
            query = (
                self._db.collection(SESSIONS_COLLECTION)
                .where(filter=FieldFilter("app_name", "==", app_name))
                .where(filter=FieldFilter("user_id", "==", user_id))
            )
            sessions = []
            for doc in query.stream():
                d = doc.to_dict()
                sessions.append(
                    Session(
                        app_name=d["app_name"],
                        user_id=d["user_id"],
                        id=doc.id,
                        state=d.get("state", {}),
                        last_update_time=d["updateTime"].timestamp(),
                    )
                )
            return ListSessionsResponse(sessions=sessions)

        return await asyncio.to_thread(_list)

    @override
    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        def _delete():
            session_ref = self._db.collection(SESSIONS_COLLECTION).document(session_id)
            session_doc = session_ref.get()
            if not session_doc.exists:
                return
            d = session_doc.to_dict()
            if d.get("user_id") != user_id or d.get("app_name") != app_name:
                return
            for doc_ref in session_ref.collection(EVENTS_SUBCOLLECTION).list_documents():
                doc_ref.delete()
            session_ref.delete()

        await asyncio.to_thread(_delete)

    async def _update_session_state(self, session_id: str, state_delta: Dict[str, Any]):
        def _update():
            session_ref = self._db.collection(SESSIONS_COLLECTION).document(session_id)
            update_data = {f"state.{k}": v for k, v in state_delta.items()}
            update_data["updateTime"] = firestore.SERVER_TIMESTAMP
            session_ref.update(update_data)

        await asyncio.to_thread(_update)

    @override
    async def append_event(self, session: Session, event: Event) -> Event:
        event = await super().append_event(session=session, event=event)
        if event.actions and event.actions.state_delta:
            await self._update_session_state(session.id, event.actions.state_delta)

        def _append():
            batch = self._db.batch()
            session_ref = self._db.collection(SESSIONS_COLLECTION).document(session.id)
            event_doc_ref = session_ref.collection(EVENTS_SUBCOLLECTION).document()
            event.id = event_doc_ref.id
            batch.set(event_doc_ref, _event_to_dict(event))
            batch.update(session_ref, {"updateTime": firestore.SERVER_TIMESTAMP})
            batch.commit()

        await asyncio.to_thread(_append)
        return event


def _event_to_dict(event: Event) -> Dict[str, Any]:
    metadata_json = {
        "partial": event.partial,
        "turn_complete": event.turn_complete,
        "interrupted": event.interrupted,
        "branch": event.branch,
        "long_running_tool_ids": (
            list(event.long_running_tool_ids) if event.long_running_tool_ids else None
        ),
    }
    if event.grounding_metadata:
        metadata_json["grounding_metadata"] = event.grounding_metadata.model_dump(
            exclude_none=True, mode="json"
        )
    event_json = {
        "author": event.author,
        "invocation_id": event.invocation_id,
        "timestamp": {
            "seconds": int(event.timestamp),
            "nanos": int((event.timestamp - int(event.timestamp)) * 1_000_000_000),
        },
        "error_code": event.error_code,
        "error_message": event.error_message,
        "event_metadata": metadata_json,
    }
    if event.actions:
        event_json["actions"] = {
            "skip_summarization": event.actions.skip_summarization,
            "state_delta": event.actions.state_delta,
            "artifact_delta": event.actions.artifact_delta,
            "transfer_agent": event.actions.transfer_to_agent,
            "escalate": event.actions.escalate,
            "requested_auth_configs": event.actions.requested_auth_configs,
        }
    if event.content:
        event_json["content"] = event.content.model_dump(exclude_none=True, mode="json")
    return event_json


def _doc_to_event(doc: firestore.DocumentSnapshot) -> Event:
    event_dict = doc.to_dict()
    event_actions = EventActions()
    if event_dict.get("actions"):
        a = event_dict["actions"]
        event_actions = EventActions(
            skip_summarization=a.get("skip_summarization"),
            state_delta=a.get("state_delta", {}),
            artifact_delta=a.get("artifact_delta", {}),
            transfer_to_agent=a.get("transfer_agent"),
            escalate=a.get("escalate"),
            requested_auth_configs=a.get("requested_auth_configs", {}),
        )
    ts = event_dict["timestamp"]
    timestamp_float = ts["seconds"] + ts.get("nanos", 0) / 1_000_000_000
    content_dict = event_dict.get("content")
    content = Content(**content_dict) if content_dict else None
    event = Event(
        id=doc.id,
        invocation_id=event_dict["invocation_id"],
        author=event_dict["author"],
        actions=event_actions,
        content=content,
        timestamp=timestamp_float,
        error_code=event_dict.get("error_code"),
        error_message=event_dict.get("error_message"),
    )
    if event_dict.get("event_metadata"):
        meta = event_dict["event_metadata"]
        event.partial = meta.get("partial")
        event.turn_complete = meta.get("turn_complete")
        event.interrupted = meta.get("interrupted")
        event.branch = meta.get("branch")
        if meta.get("grounding_metadata"):
            event.grounding_metadata = GroundingMetadata(**meta["grounding_metadata"])
        event.long_running_tool_ids = meta.get("long_running_tool_ids") and set(
            meta["long_running_tool_ids"]
        )
    return event


def create_firestore_session_service(project: str, database: str):
    """Create FirestoreSessionService. Requires project (FIRESTORE_PROJECT) and database (FIRESTORE_DATABASE)."""
    return FirestoreSessionService(project=project, database=database)
