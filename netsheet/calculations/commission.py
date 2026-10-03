"""Real estate compensation lines.

No standard rate is assumed anywhere. Each line is whatever the agent enters:
  - "percent":           price x percent
  - "flat":              a fixed dollar amount
  - "percent_plus_flat": price x percent + a fixed dollar amount
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from ..money import fmt, round_cents

METHODS = {
    "percent": "Percentage of sale price",
    "flat": "Flat dollar amount",
    "percent_plus_flat": "Percentage plus flat amount",
}


@dataclass
class CommissionResult:
    amount: Decimal | None
    steps: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def calculate_commission(
    price: Decimal | None,
    method: str,
    percent: Decimal | None,
    flat: Decimal | None,
) -> CommissionResult:
    if method not in METHODS:
        return CommissionResult(None, problems=[f"Unknown method '{method}'"])

    steps: list[str] = []
    total = Decimal("0")

    if method in ("percent", "percent_plus_flat"):
        if percent is None:
            return CommissionResult(None, problems=["Enter a percentage."])
        if price is None:
            return CommissionResult(None, problems=["Enter a sale price so the percentage can be calculated."])
        part = round_cents(price * percent / Decimal("100"))
        steps.append(f"{fmt(price)} × {percent.normalize():f}% = {fmt(part)}")
        total += part

    if method in ("flat", "percent_plus_flat"):
        if flat is None:
            return CommissionResult(None, problems=["Enter a flat dollar amount."])
        steps.append(f"Flat amount: {fmt(flat)}")
        total += flat

    if method == "percent_plus_flat":
        steps.append(f"Total: {fmt(total)}")
    return CommissionResult(round_cents(total), steps=steps)
