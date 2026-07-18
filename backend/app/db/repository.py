"""Persistence boundary: application workflows depend on EventRepository only."""
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column
from app.core.config import settings
from app.db.database import Base, SessionLocal
from app.models.anomaly import AnomalyEvent


class EventRepository(ABC):
    provider_name: str
    @abstractmethod
    async def save_event(self, event: AnomalyEvent) -> None: ...
    @abstractmethod
    async def update_event_insight(self, event_id: str, insight: str) -> None: ...
    @abstractmethod
    async def get_event(self, event_id: str) -> AnomalyEvent | None: ...
    @abstractmethod
    async def list_events(self, limit: int) -> list[AnomalyEvent]: ...


class EventRow(Base):
    __tablename__ = "anomaly_events"
    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    heart_rate: Mapped[float] = mapped_column(Float); spo2: Mapped[float] = mapped_column(Float)
    accelerometer_magnitude: Mapped[float] = mapped_column(Float); anomaly_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float); severity: Mapped[str] = mapped_column(String)
    llm_insight: Mapped[str | None] = mapped_column(Text, nullable=True)


class SQLiteEventRepository(EventRepository):
    provider_name = "sqlite"
    async def save_event(self, event: AnomalyEvent) -> None:
        with SessionLocal.begin() as session: session.add(EventRow(**event.model_dump()))
    async def update_event_insight(self, event_id: str, insight: str) -> None:
        with SessionLocal.begin() as session:
            row = session.get(EventRow, event_id)
            if row: row.llm_insight = insight
    async def get_event(self, event_id: str) -> AnomalyEvent | None:
        with SessionLocal() as session:
            row = session.get(EventRow, event_id)
            return AnomalyEvent.model_validate(row, from_attributes=True) if row else None
    async def list_events(self, limit: int) -> list[AnomalyEvent]:
        with SessionLocal() as session:
            rows = session.scalars(select(EventRow).order_by(EventRow.timestamp.desc()).limit(limit)).all()
            return [AnomalyEvent.model_validate(row, from_attributes=True) for row in rows]


class DynamoDBEventRepository(EventRepository):
    """Optional production repository. It creates no AWS resources."""
    provider_name = "dynamodb"
    def __init__(self, table_name: str, region: str | None) -> None:
        import boto3  # Imported only when DynamoDB is explicitly selected.
        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)
    @staticmethod
    def _item(event: AnomalyEvent) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        item = event.model_dump(mode="json")
        item.update({"created_at": now, "updated_at": now})
        return item
    async def save_event(self, event: AnomalyEvent) -> None:
        await asyncio.to_thread(self.table.put_item, Item=self._item(event))
    async def update_event_insight(self, event_id: str, insight: str) -> None:
        await asyncio.to_thread(self.table.update_item, Key={"event_id": event_id}, UpdateExpression="SET llm_insight = :i, updated_at = :u", ExpressionAttributeValues={":i": insight, ":u": datetime.now(timezone.utc).isoformat()})
    async def get_event(self, event_id: str) -> AnomalyEvent | None:
        response = await asyncio.to_thread(self.table.get_item, Key={"event_id": event_id})
        item = response.get("Item")
        return AnomalyEvent.model_validate(item) if item else None
    async def list_events(self, limit: int) -> list[AnomalyEvent]:
        response = await asyncio.to_thread(self.table.scan, Limit=limit)
        items = sorted(response.get("Items", []), key=lambda item: item["timestamp"], reverse=True)
        return [AnomalyEvent.model_validate(item) for item in items[:limit]]


def get_event_repository() -> EventRepository:
    if settings.event_database_provider == "sqlite": return SQLiteEventRepository()
    if settings.event_database_provider == "dynamodb":
        if not settings.dynamodb_table_name: raise RuntimeError("DYNAMODB_TABLE_NAME is required for DynamoDB")
        return DynamoDBEventRepository(settings.dynamodb_table_name, settings.aws_region)
    raise RuntimeError(f"Unsupported EVENT_DATABASE_PROVIDER: {settings.event_database_provider}")
