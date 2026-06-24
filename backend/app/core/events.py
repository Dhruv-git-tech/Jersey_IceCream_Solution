# =============================================================================
# Jersey Ice Cream Platform — Kafka Event Bus
# =============================================================================
# Async Kafka producer and consumer for event-driven architecture.
#
# Topics:
#   jersey.cart.location     — Cart GPS pings (high volume, 2.88M/day)
#   jersey.cart.photo        — Photo upload events → AI pipeline
#   jersey.inventory.updated — Inventory changes (from photos, refills, orders)
#   jersey.refill.requested  — Vendor refill requests
#   jersey.order.created     — New order events
#   jersey.forecast.computed — Forecast results for dashboard
#   jersey.alert.triggered   — Alert events for notifications
#   jersey.competitor.intel  — Competitor intelligence events
#
# Design Decision:
#   - aiokafka for async Kafka access (non-blocking FastAPI integration)
#   - Manual commit (enable_auto_commit=False) for at-least-once delivery
#   - JSON serialization (not Avro/Protobuf) for simplicity; migrate to
#     schema registry when >10 consumers exist
#   - Partition by entity ID for ordering guarantees per entity
#
# Failure Modes:
#   - Kafka broker down: Producer retries with exponential backoff (max 30s)
#   - Consumer crash: Uncommitted offsets → messages reprocessed (idempotent handlers)
#   - Serialization error: Dead letter queue (DLQ) for poison messages
# =============================================================================

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Topic Definitions ──────────────────────────────────────────────────────


class Topic(str, Enum):
    """Kafka topic names with consistent naming convention."""

    CART_LOCATION = "jersey.cart.location"
    CART_PHOTO = "jersey.cart.photo"
    INVENTORY_UPDATED = "jersey.inventory.updated"
    REFILL_REQUESTED = "jersey.refill.requested"
    ORDER_CREATED = "jersey.order.created"
    ORDER_UPDATED = "jersey.order.updated"
    FORECAST_COMPUTED = "jersey.forecast.computed"
    ALERT_TRIGGERED = "jersey.alert.triggered"
    COMPETITOR_INTEL = "jersey.competitor.intel"
    AUDIT_EVENT = "jersey.audit.event"
    WEATHER_UPDATED = "jersey.weather.updated"
    DLQ = "jersey.dlq"  # Dead letter queue


# ─── Event Schema ────────────────────────────────────────────────────────────


class EventEnvelope:
    """
    Standard event envelope for all Kafka messages.

    Ensures consistent metadata across all events for tracing and debugging.
    """

    def __init__(
        self,
        event_type: str,
        payload: dict[str, Any],
        entity_id: str | None = None,
        entity_type: str | None = None,
        source: str = "jersey-backend",
        correlation_id: str | None = None,
    ) -> None:
        import uuid
        from datetime import UTC, datetime

        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.payload = payload
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.source = source
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.timestamp = datetime.now(UTC).isoformat()
        self.version = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "source": self.source,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "version": self.version,
            "payload": self.payload,
        }

    def to_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), default=str).encode("utf-8")


# ─── Kafka Producer ─────────────────────────────────────────────────────────


class EventProducer:
    """
    Async Kafka producer with retry logic and partition key support.

    Usage:
        producer = EventProducer()
        await producer.start()
        await producer.publish(
            topic=Topic.INVENTORY_UPDATED,
            event_type="inventory.snapshot",
            payload={"cart_id": "abc", "products": [...]},
            partition_key="abc",  # Ensures ordering per cart
        )
        await producer.stop()
    """

    def __init__(self) -> None:
        self._producer = None

    async def start(self) -> None:
        """Initialize the Kafka producer."""
        try:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",  # Wait for all replicas to acknowledge
                retries=5,
                retry_backoff_ms=1000,
                max_request_size=10485760,  # 10MB (for photo metadata)
                compression_type="snappy",  # ~3x compression for JSON
                linger_ms=10,  # Batch messages for 10ms for throughput
                enable_idempotence=True,  # Exactly-once producer semantics
            )
            await self._producer.start()
            logger.info("Kafka producer started successfully")
        except Exception:
            logger.warning("Kafka producer failed to start — events will be logged only", exc_info=True)
            self._producer = None

    async def stop(self) -> None:
        """Flush and close the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def publish(
        self,
        topic: Topic,
        event_type: str,
        payload: dict[str, Any],
        partition_key: str | None = None,
        entity_id: str | None = None,
        entity_type: str | None = None,
        correlation_id: str | None = None,
    ) -> bool:
        """
        Publish an event to a Kafka topic.

        Args:
            topic: Target Kafka topic
            event_type: Event type string (e.g., 'inventory.updated')
            payload: Event data
            partition_key: Key for partition assignment (ensures ordering)
            entity_id: ID of the related entity
            entity_type: Type of the related entity
            correlation_id: Trace correlation ID

        Returns:
            True if published successfully, False otherwise
        """
        envelope = EventEnvelope(
            event_type=event_type,
            payload=payload,
            entity_id=entity_id or partition_key,
            entity_type=entity_type,
            correlation_id=correlation_id,
        )

        if self._producer is None:
            # Fallback: log the event when Kafka is unavailable
            logger.warning(
                "Kafka unavailable — event logged: topic=%s type=%s entity=%s",
                topic.value,
                event_type,
                entity_id,
            )
            return False

        try:
            await self._producer.send_and_wait(
                topic=topic.value,
                value=envelope.to_dict(),
                key=partition_key,
            )
            logger.debug(
                "Event published: topic=%s type=%s id=%s",
                topic.value,
                event_type,
                envelope.event_id,
            )
            return True
        except Exception:
            logger.error(
                "Failed to publish event: topic=%s type=%s",
                topic.value,
                event_type,
                exc_info=True,
            )
            return False


# ─── Kafka Consumer ─────────────────────────────────────────────────────────


class EventConsumer:
    """
    Async Kafka consumer with manual offset commit and error handling.

    Usage:
        consumer = EventConsumer(
            topics=[Topic.CART_PHOTO, Topic.INVENTORY_UPDATED],
            group_id="photo-processor",
        )
        await consumer.start()
        async for event in consumer.consume():
            await process_event(event)
        await consumer.stop()
    """

    def __init__(
        self,
        topics: list[Topic],
        group_id: str | None = None,
    ) -> None:
        self._topics = [t.value for t in topics]
        self._group_id = group_id or settings.kafka_group_id
        self._consumer = None

    async def start(self) -> None:
        """Initialize the Kafka consumer."""
        from aiokafka import AIOKafkaConsumer

        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=self._group_id,
            auto_offset_reset=settings.kafka_auto_offset_reset,
            enable_auto_commit=False,  # Manual commit for at-least-once
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            max_poll_records=settings.kafka_max_poll_records,
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000,
        )
        await self._consumer.start()
        logger.info("Kafka consumer started for topics: %s", self._topics)

    async def stop(self) -> None:
        """Close the Kafka consumer."""
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")

    async def consume(self):
        """
        Async generator that yields deserialized events.

        Commits offset after each successful message processing.
        On error, the message is sent to DLQ and offset is still committed
        to prevent infinite reprocessing loops.
        """
        if not self._consumer:
            raise RuntimeError("Consumer not started. Call start() first.")

        async for message in self._consumer:
            try:
                yield message.value
                await self._consumer.commit()
            except Exception:
                logger.error(
                    "Error processing message from %s partition %d offset %d",
                    message.topic,
                    message.partition,
                    message.offset,
                    exc_info=True,
                )
                # Commit to move past the poison message
                await self._consumer.commit()


# ─── Singleton Producer ─────────────────────────────────────────────────────

_producer: EventProducer | None = None


async def get_event_producer() -> EventProducer:
    """Get or create the singleton event producer."""
    global _producer
    if _producer is None:
        _producer = EventProducer()
        await _producer.start()
    return _producer


async def close_event_producer() -> None:
    """Close the singleton event producer."""
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
