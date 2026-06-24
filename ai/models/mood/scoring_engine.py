# =============================================================================
# Jersey Ice Cream Platform — Mood Commerce Scoring Engine
# =============================================================================
# Predicts demand spikes from emotional/cultural events.
#
# Mathematical Model:
#   MIS(event) = Base_Impact × Temporal_Decay × Spatial_Decay × Category_Multiplier
#
#   Where:
#     Base_Impact ∈ [0, 1] — Pre-calibrated per event type
#     Temporal_Decay = exp(-λ × hours_since_event), λ = 0.15
#     Spatial_Decay = max(0, 1 - distance_km / impact_radius_km)
#     Category_Multiplier — Product-specific boost factors
#
#   Composite Score:
#     Cart_Mood_Score = Σ MIS(event_i) for all active events
#     Demand_Multiplier = 1 + tanh(Cart_Mood_Score)  → bounded [0, 2]
#
#   Why tanh: Prevents unbounded multiplication from stacking events.
#   tanh(x) ∈ (-1, 1), so multiplier ∈ (0, 2).
# =============================================================================

from __future__ import annotations

import math
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# ─── Event Impact Configuration ─────────────────────────────────────────────

@dataclass
class EventImpactConfig:
    """Pre-calibrated impact parameters for each event type."""

    base_impact: float
    impact_radius_km: float
    typical_duration_hours: float
    category_multipliers: dict[str, float]
    temporal_decay_lambda: float = 0.15  # Half-life ≈ 4.6 hours


# Event-specific impact configurations
EVENT_IMPACT_CONFIGS: dict[str, EventImpactConfig] = {
    "india_cricket_win": EventImpactConfig(
        base_impact=0.85,
        impact_radius_km=50.0,
        typical_duration_hours=6.0,
        category_multipliers={
            "cone": 1.3, "cup": 1.1, "bar": 1.2,
            "premium": 1.4, "family_pack": 1.2,
        },
    ),
    "ipl_match": EventImpactConfig(
        base_impact=0.70,
        impact_radius_km=30.0,
        typical_duration_hours=4.0,
        category_multipliers={
            "cone": 1.2, "cup": 1.2, "bar": 1.1,
            "premium": 1.3, "family_pack": 1.1,
        },
    ),
    "ipl_final": EventImpactConfig(
        base_impact=0.90,
        impact_radius_km=100.0,
        typical_duration_hours=8.0,
        category_multipliers={
            "cone": 1.4, "cup": 1.3, "bar": 1.3,
            "premium": 1.5, "family_pack": 1.4,
        },
    ),
    "school_result_day": EventImpactConfig(
        base_impact=0.60,
        impact_radius_km=10.0,
        typical_duration_hours=8.0,
        category_multipliers={
            "cone": 1.2, "cup": 1.3, "family_pack": 1.5,
            "premium": 1.3, "bulk": 1.4,
        },
    ),
    "local_festival": EventImpactConfig(
        base_impact=0.75,
        impact_radius_km=15.0,
        typical_duration_hours=12.0,
        category_multipliers={
            "kulfi": 1.4, "cone": 1.2, "premium": 1.3,
            "family_pack": 1.3, "bulk": 1.5,
        },
    ),
    "diwali": EventImpactConfig(
        base_impact=0.85,
        impact_radius_km=100.0,
        typical_duration_hours=48.0,
        category_multipliers={
            "premium": 1.6, "family_pack": 1.5, "bulk": 1.7,
            "kulfi": 1.3, "cone": 1.1,
        },
    ),
    "holi": EventImpactConfig(
        base_impact=0.80,
        impact_radius_km=100.0,
        typical_duration_hours=12.0,
        category_multipliers={
            "kulfi": 1.5, "cone": 1.4, "bar": 1.3,
            "cup": 1.3, "premium": 1.2,
        },
    ),
    "wedding_season": EventImpactConfig(
        base_impact=0.50,
        impact_radius_km=20.0,
        typical_duration_hours=720.0,  # 30 days
        category_multipliers={
            "bulk": 1.6, "premium": 1.5, "family_pack": 1.4,
            "kulfi": 1.3, "cup": 1.1,
        },
        temporal_decay_lambda=0.001,  # Very slow decay for long events
    ),
    "heat_wave": EventImpactConfig(
        base_impact=0.90,
        impact_radius_km=100.0,
        typical_duration_hours=24.0,
        category_multipliers={
            "bar": 1.5, "cone": 1.5, "cup": 1.4,
            "kulfi": 1.6, "premium": 1.3,
        },
    ),
    "rain_storm": EventImpactConfig(
        base_impact=-0.60,  # Negative = demand decrease
        impact_radius_km=50.0,
        typical_duration_hours=6.0,
        category_multipliers={
            "cone": 0.7, "bar": 0.7, "cup": 0.8,
            "kulfi": 0.6, "premium": 0.9,
        },
    ),
    "exam_period": EventImpactConfig(
        base_impact=-0.30,  # Slight decrease during exams
        impact_radius_km=10.0,
        typical_duration_hours=240.0,  # 10 days
        category_multipliers={
            "cone": 0.9, "cup": 0.9, "bar": 0.9,
        },
        temporal_decay_lambda=0.005,
    ),
}


# ─── Scoring Engine ─────────────────────────────────────────────────────────

@dataclass
class MoodEvent:
    """An active event affecting demand."""

    event_type: str
    event_start: datetime
    event_end: datetime | None
    location_lat: float
    location_lng: float
    impact_radius_km: float
    base_impact: float
    title: str = ""
    metadata: dict[str, Any] | None = None


@dataclass
class MoodScore:
    """Computed mood score for a specific location and time."""

    composite_score: float  # Raw composite score
    demand_multiplier: float  # 1 + tanh(composite_score), bounded [0, 2]
    contributing_events: list[dict[str, Any]]
    category_multipliers: dict[str, float]
    computed_at: datetime


class MoodCommerceEngine:
    """
    Mood Commerce scoring engine.

    Computes demand multipliers based on active emotional/cultural events
    near a cart's location.

    Usage:
        engine = MoodCommerceEngine()
        score = engine.compute_mood_score(
            cart_lat=19.076,
            cart_lng=72.877,
            events=[...],
            product_category="cone",
        )
        adjusted_demand = base_demand * score.demand_multiplier
    """

    def compute_mood_score(
        self,
        cart_lat: float,
        cart_lng: float,
        events: list[MoodEvent],
        timestamp: datetime | None = None,
        product_category: str | None = None,
    ) -> MoodScore:
        """
        Compute the composite mood score for a cart location.

        Args:
            cart_lat: Cart latitude
            cart_lng: Cart longitude
            events: List of active events
            timestamp: Current time (default: now)
            product_category: Product category for category-specific multiplier

        Returns:
            MoodScore with composite score, demand multiplier, and contributing events
        """
        now = timestamp or datetime.now(UTC)
        composite_score = 0.0
        contributing_events = []
        category_multipliers: dict[str, float] = {}

        for event in events:
            # Get event config (or use event's own parameters)
            config = EVENT_IMPACT_CONFIGS.get(event.event_type)

            if config is None:
                # Use event's direct parameters
                base_impact = event.base_impact
                decay_lambda = 0.15
                cat_multipliers = {}
            else:
                base_impact = config.base_impact
                decay_lambda = config.temporal_decay_lambda
                cat_multipliers = config.category_multipliers

            # 1. Temporal Decay
            hours_since_start = (now - event.event_start).total_seconds() / 3600.0

            # If event hasn't started yet, no impact
            if hours_since_start < 0:
                continue

            # If event has ended, decay from end time
            if event.event_end and now > event.event_end:
                hours_since_end = (now - event.event_end).total_seconds() / 3600.0
                temporal_decay = math.exp(-decay_lambda * hours_since_end)
            else:
                # During the event — full impact with slight buildup
                temporal_decay = min(1.0, hours_since_start / 0.5)  # Ramp up in first 30 min

            # 2. Spatial Decay
            distance_km = self._haversine_distance(
                cart_lat, cart_lng,
                event.location_lat, event.location_lng,
            )
            radius = event.impact_radius_km or (config.impact_radius_km if config else 50.0)
            spatial_decay = max(0.0, 1.0 - (distance_km / radius))

            if spatial_decay <= 0:
                continue  # Event too far away

            # 3. Category Multiplier
            category_mult = 1.0
            if product_category and cat_multipliers:
                category_mult = cat_multipliers.get(product_category, 1.0)

            # Compute MIS (Mood Impact Score)
            mis = base_impact * temporal_decay * spatial_decay * category_mult
            composite_score += mis

            # Track contributing events
            contributing_events.append({
                "event_type": event.event_type,
                "title": event.title,
                "mis": round(mis, 4),
                "temporal_decay": round(temporal_decay, 4),
                "spatial_decay": round(spatial_decay, 4),
                "distance_km": round(distance_km, 2),
                "base_impact": base_impact,
            })

            # Aggregate category multipliers
            for cat, mult in cat_multipliers.items():
                current = category_multipliers.get(cat, 1.0)
                # Combine multiplicatively: existing × (1 + (mult-1) × spatial_decay × temporal_decay)
                adjusted = 1.0 + (mult - 1.0) * spatial_decay * temporal_decay
                category_multipliers[cat] = round(current * adjusted, 4)

        # Composite demand multiplier using tanh bounding
        demand_multiplier = 1.0 + math.tanh(composite_score)
        demand_multiplier = max(0.0, min(2.0, demand_multiplier))

        return MoodScore(
            composite_score=round(composite_score, 4),
            demand_multiplier=round(demand_multiplier, 4),
            contributing_events=contributing_events,
            category_multipliers=category_multipliers,
            computed_at=now,
        )

    @staticmethod
    def _haversine_distance(
        lat1: float, lng1: float,
        lat2: float, lng2: float,
    ) -> float:
        """
        Calculate great-circle distance between two points in km.

        Uses the Haversine formula.
        Time Complexity: O(1)
        """
        R = 6371.0  # Earth's radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
