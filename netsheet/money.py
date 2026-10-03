"""Money helpers.

All money math uses Python's Decimal type (exact base-10 arithmetic), never
floating point, so cents are never lost to rounding errors. Amounts are rounded
to the cent only where a line item is finalized, using "round half up" (the
ordinary rounding people do by hand: $0.005 becomes $0.01).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


class MoneyError(ValueError):
    """Raised when text cannot be read as a dollar amount."""


def parse_money(text: str | None) -> Decimal | None:
    """Read a dollar amount typed by a person.

    Accepts "250000", "$250,000", "250,000.50". Returns None for blank input.
    Raises MoneyError for anything else rather than guessing.
    """
    if text is None:
        return None
    cleaned = str(text).strip().replace("$", "").replace(",", "").replace(" ", "")
    if cleaned == "":
        return None
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise MoneyError(f"'{text}' is not a dollar amount") from exc
    if not value.is_finite():
        raise MoneyError(f"'{text}' is not a dollar amount")
    if value.as_tuple().exponent < -2:
        raise MoneyError(f"'{text}' has more than two decimal places")
    return -value if negative else value


def parse_percent(text: str | None) -> Decimal | None:
    """Read a percentage such as "3", "3%", or "2.75". Blank returns None."""
    if text is None:
        return None
    cleaned = str(text).strip().replace("%", "").replace(" ", "")
    if cleaned == "":
        return None
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise MoneyError(f"'{text}' is not a percentage") from exc
    if not value.is_finite() or value < 0 or value > 100:
        raise MoneyError(f"'{text}' is not a percentage between 0 and 100")
    return value


def round_cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(value: Decimal | None, blank: str = "—") -> str:
    """Format as $1,234.56 (negative as -$1,234.56)."""
    if value is None:
        return blank
    value = round_cents(value)
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def to_str(value: Decimal | None) -> str:
    """Store a Decimal as text in the saved record (exact, no float)."""
    return "" if value is None else str(value)
