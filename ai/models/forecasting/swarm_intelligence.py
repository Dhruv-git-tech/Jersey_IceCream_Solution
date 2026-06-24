# =============================================================================
# Jersey Ice Cream Platform — Swarm Cart Intelligence
# =============================================================================
# Treats every cart as a node in a graph for spatial analytics.
#
# Algorithms:
#   - DBSCAN: Density-based clustering for demand zones, O(n log n) with R-tree
#   - Demand Heatmap: Kernel density estimation on geohash grid, O(n)
#   - Demand Migration: Detect demand movement between adjacent cells
#   - Spatial Autocorrelation (Moran's I): Identify spatial demand patterns
#
# DSA Justification:
#   - Adjacency list representation: O(V + E) space
#   - DBSCAN with spatial index: O(n log n) time
#   - Heatmap generation: O(n) per frame
#   - Moran's I: O(n²) precomputed nightly (acceptable for 10K carts)
# =============================================================================

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CartNode:
    """Cart as a graph node with spatial and demand attributes."""

    cart_id: str
    latitude: float
    longitude: float
    geohash: str
    current_demand: float = 0.0
    inventory_level: float = 0.0
    sales_velocity: float = 0.0
    mood_score: float = 0.0
    territory_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DemandCluster:
    """A cluster of carts forming a demand zone."""

    cluster_id: int
    center_lat: float
    center_lng: float
    carts: list[CartNode]
    total_demand: float
    avg_sales_velocity: float
    radius_km: float
    geohash_cells: set[str]


@dataclass
class HeatmapCell:
    """Single cell in the demand heatmap grid."""

    geohash: str
    latitude: float
    longitude: float
    demand_intensity: float
    cart_count: int
    avg_sales_velocity: float
    trend: str  # "rising", "stable", "falling"


@dataclass
class MigrationEvent:
    """Demand migration between two geohash cells."""

    source_geohash: str
    target_geohash: str
    demand_delta: float
    timestamp: str
    confidence: float


class SwarmIntelligenceEngine:
    """
    Swarm-based cart intelligence engine.

    Treats the cart network as a spatial graph for:
    1. Demand zone detection (DBSCAN clustering)
    2. Real-time heatmap generation
    3. Demand migration tracking
    4. Territory optimization suggestions
    """

    def __init__(self, eps_km: float = 2.0, min_samples: int = 3) -> None:
        """
        Args:
            eps_km: DBSCAN neighborhood radius in km
            min_samples: Minimum carts per cluster
        """
        self.eps_km = eps_km
        self.min_samples = min_samples

    # ─── DBSCAN Clustering ──────────────────────────────────────────────

    def cluster_demand_zones(
        self,
        carts: list[CartNode],
    ) -> list[DemandCluster]:
        """
        Cluster carts into demand zones using DBSCAN.

        Why DBSCAN:
        - Doesn't require pre-specifying K (unlike K-means)
        - Handles irregular cart distributions
        - Identifies noise points (isolated carts)

        Time Complexity: O(n log n) with ball-tree spatial index
        Space Complexity: O(n)
        """
        if len(carts) < self.min_samples:
            return []

        try:
            from sklearn.cluster import DBSCAN
            from sklearn.metrics.pairwise import haversine_distances

            # Convert to radians for haversine
            coords = np.array(
                [[math.radians(c.latitude), math.radians(c.longitude)] for c in carts]
            )

            # DBSCAN with haversine metric
            # eps in radians: km / earth_radius_km
            eps_rad = self.eps_km / 6371.0

            clustering = DBSCAN(
                eps=eps_rad,
                min_samples=self.min_samples,
                metric="haversine",
                algorithm="ball_tree",  # O(n log n) for haversine
            )
            labels = clustering.fit_predict(coords)

        except ImportError:
            logger.warning("sklearn not available — using simple geohash clustering")
            labels = self._simple_geohash_clustering(carts)

        # Build clusters
        clusters: dict[int, list[CartNode]] = defaultdict(list)
        for cart, label in zip(carts, labels):
            if label >= 0:  # -1 = noise
                clusters[label].append(cart)

        result = []
        for cluster_id, cluster_carts in clusters.items():
            lats = [c.latitude for c in cluster_carts]
            lngs = [c.longitude for c in cluster_carts]
            center_lat = np.mean(lats)
            center_lng = np.mean(lngs)

            # Calculate cluster radius
            max_dist = max(
                self._haversine(center_lat, center_lng, c.latitude, c.longitude)
                for c in cluster_carts
            )

            total_demand = sum(c.current_demand for c in cluster_carts)
            avg_velocity = np.mean([c.sales_velocity for c in cluster_carts])
            geohash_cells = set(c.geohash[:5] for c in cluster_carts)

            result.append(
                DemandCluster(
                    cluster_id=cluster_id,
                    center_lat=float(center_lat),
                    center_lng=float(center_lng),
                    carts=cluster_carts,
                    total_demand=total_demand,
                    avg_sales_velocity=float(avg_velocity),
                    radius_km=round(max_dist, 2),
                    geohash_cells=geohash_cells,
                )
            )

        # Sort by demand (highest first)
        result.sort(key=lambda c: c.total_demand, reverse=True)
        logger.info("DBSCAN found %d demand clusters from %d carts", len(result), len(carts))
        return result

    # ─── Demand Heatmap ─────────────────────────────────────────────────

    def generate_heatmap(
        self,
        carts: list[CartNode],
        geohash_precision: int = 5,
        previous_heatmap: dict[str, float] | None = None,
    ) -> list[HeatmapCell]:
        """
        Generate a demand heatmap by aggregating cart data per geohash cell.

        Each cell's intensity = sum of sales velocities of carts in that cell.

        Time Complexity: O(n) single pass over carts
        Space Complexity: O(g) where g = unique geohash cells

        Args:
            carts: List of cart nodes
            geohash_precision: Geohash precision for cell size (5 ≈ 5km × 5km)
            previous_heatmap: Previous intensity map for trend detection
        """
        # Aggregate by geohash cell
        cells: dict[str, dict] = defaultdict(
            lambda: {
                "lats": [],
                "lngs": [],
                "demands": [],
                "velocities": [],
                "count": 0,
            }
        )

        for cart in carts:
            cell_hash = cart.geohash[:geohash_precision]
            cell = cells[cell_hash]
            cell["lats"].append(cart.latitude)
            cell["lngs"].append(cart.longitude)
            cell["demands"].append(cart.current_demand)
            cell["velocities"].append(cart.sales_velocity)
            cell["count"] += 1

        # Build heatmap cells
        result = []
        for geohash, data in cells.items():
            intensity = sum(data["velocities"])
            avg_velocity = np.mean(data["velocities"]) if data["velocities"] else 0.0

            # Determine trend
            trend = "stable"
            if previous_heatmap and geohash in previous_heatmap:
                prev_intensity = previous_heatmap[geohash]
                if intensity > prev_intensity * 1.2:
                    trend = "rising"
                elif intensity < prev_intensity * 0.8:
                    trend = "falling"

            result.append(
                HeatmapCell(
                    geohash=geohash,
                    latitude=float(np.mean(data["lats"])),
                    longitude=float(np.mean(data["lngs"])),
                    demand_intensity=round(intensity, 2),
                    cart_count=data["count"],
                    avg_sales_velocity=round(float(avg_velocity), 2),
                    trend=trend,
                )
            )

        # Sort by intensity (hottest first)
        result.sort(key=lambda c: c.demand_intensity, reverse=True)
        return result

    # ─── Demand Migration Detection ─────────────────────────────────────

    def detect_demand_migration(
        self,
        current_heatmap: list[HeatmapCell],
        previous_heatmap: list[HeatmapCell],
        threshold: float = 2.0,
    ) -> list[MigrationEvent]:
        """
        Detect demand migration between adjacent geohash cells.

        Algorithm:
        1. Compute delta (current - previous) per cell
        2. Find adjacent cell pairs with complementary deltas
           (one positive, neighbor negative)
        3. These indicate demand "moving" from one area to another

        Time Complexity: O(g²) where g = geohash cells (typically < 200)
        """
        # Build lookup maps
        current_map = {c.geohash: c.demand_intensity for c in current_heatmap}
        previous_map = {c.geohash: c.demand_intensity for c in previous_heatmap}

        # Compute deltas
        all_cells = set(current_map.keys()) | set(previous_map.keys())
        deltas: dict[str, float] = {}
        for cell in all_cells:
            curr = current_map.get(cell, 0.0)
            prev = previous_map.get(cell, 0.0)
            deltas[cell] = curr - prev

        # Find migration patterns (adjacent cells with complementary deltas)
        migrations = []
        cells_list = list(deltas.keys())

        for i, cell_a in enumerate(cells_list):
            delta_a = deltas[cell_a]
            if delta_a >= 0:
                continue  # Only look at cells that lost demand

            for cell_b in cells_list[i + 1:]:
                delta_b = deltas[cell_b]
                if delta_b <= 0:
                    continue  # Only pair with cells that gained demand

                # Check if adjacent (geohash prefix match)
                if self._are_adjacent_geohashes(cell_a, cell_b):
                    migration_amount = min(abs(delta_a), delta_b)
                    if migration_amount >= threshold:
                        confidence = min(1.0, migration_amount / max(abs(delta_a), delta_b))
                        migrations.append(
                            MigrationEvent(
                                source_geohash=cell_a,
                                target_geohash=cell_b,
                                demand_delta=round(migration_amount, 2),
                                timestamp=str(
                                    __import__("datetime").datetime.now(
                                        __import__("datetime").UTC
                                    ).isoformat()
                                ),
                                confidence=round(confidence, 3),
                            )
                        )

        migrations.sort(key=lambda m: m.demand_delta, reverse=True)
        return migrations

    # ─── Helpers ────────────────────────────────────────────────────────

    def _simple_geohash_clustering(self, carts: list[CartNode]) -> list[int]:
        """Simple fallback clustering by geohash prefix (when sklearn unavailable)."""
        cell_carts: dict[str, list[int]] = defaultdict(list)
        for i, cart in enumerate(carts):
            cell_carts[cart.geohash[:4]].append(i)

        labels = [-1] * len(carts)
        cluster_id = 0
        for cell, indices in cell_carts.items():
            if len(indices) >= self.min_samples:
                for idx in indices:
                    labels[idx] = cluster_id
                cluster_id += 1
        return labels

    @staticmethod
    def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Haversine distance in km."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(
            math.radians(lat2)
        ) * math.sin(dlng / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _are_adjacent_geohashes(gh1: str, gh2: str) -> bool:
        """
        Check if two geohashes are adjacent (share a prefix of length-1).

        This is a simplified adjacency check. Full implementation would use
        geohash neighbor computation, but prefix match covers most cases.
        """
        if len(gh1) < 2 or len(gh2) < 2:
            return False
        # Adjacent if they share prefix of length (n-1)
        return gh1[:-1] == gh2[:-1]
