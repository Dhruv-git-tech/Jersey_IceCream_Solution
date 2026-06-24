# =============================================================================
# Jersey Ice Cream Platform — Pagination Utilities
# =============================================================================

from __future__ import annotations

from math import ceil


def calculate_pagination(total: int, page: int, page_size: int) -> dict:
    """
    Calculate pagination metadata.

    Returns:
        dict with total, page, page_size, total_pages, has_next, has_prev
    """
    total_pages = max(1, ceil(total / page_size))
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


def generate_order_number(prefix: str = "ORD") -> str:
    """
    Generate a unique, human-readable order number.

    Format: {prefix}-{YYYYMMDD}-{random_6}
    Example: ORD-20260622-A3F2K9
    """
    import random
    import string
    from datetime import UTC, datetime

    date_part = datetime.now(UTC).strftime("%Y%m%d")
    random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))  # noqa: S311
    return f"{prefix}-{date_part}-{random_part}"
