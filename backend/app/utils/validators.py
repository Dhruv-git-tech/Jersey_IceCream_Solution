# =============================================================================
# Jersey Ice Cream Platform — Validation Utilities
# =============================================================================

from __future__ import annotations

import re


def validate_gstin(gstin: str) -> bool:
    """
    Validate Indian GSTIN (Goods and Services Tax Identification Number).

    Format: 2 digits (state code) + 10 chars (PAN) + 1 digit + Z + 1 check digit
    Example: 27AAPFU0939F1ZV
    """
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(pattern, gstin.upper()))


def validate_pan(pan: str) -> bool:
    """
    Validate Indian PAN card number.

    Format: 5 uppercase letters + 4 digits + 1 uppercase letter
    Example: ABCDE1234F
    """
    pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
    return bool(re.match(pattern, pan.upper()))


def validate_indian_phone(phone: str) -> bool:
    """
    Validate Indian phone number.

    Accepts: +91XXXXXXXXXX, 91XXXXXXXXXX, 0XXXXXXXXXX, XXXXXXXXXX
    Must be 10 digits after removing country/area code.
    """
    # Strip non-digits
    digits = re.sub(r"[^\d]", "", phone)

    # Remove country code
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]

    # Validate 10-digit mobile number
    return bool(re.match(r"^[6-9]\d{9}$", digits))


def validate_pincode(pincode: str) -> bool:
    """
    Validate Indian PIN code.

    Format: 6 digits, first digit 1-9
    """
    return bool(re.match(r"^[1-9][0-9]{5}$", pincode))


def sanitize_string(value: str, max_length: int = 255) -> str:
    """
    Sanitize user input string.

    - Strip whitespace
    - Remove null bytes
    - Truncate to max length
    - Remove control characters
    """
    if not value:
        return value
    # Remove null bytes and control characters (except newline, tab)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
    return cleaned.strip()[:max_length]
