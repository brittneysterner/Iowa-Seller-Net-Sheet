"""Mortgage / lien payoffs.

The payoff amount is whatever the agent enters (ideally from a lender payoff
statement). The good-through date and daily interest (per diem) are OPTIONAL.
Only when both are entered, and the closing date is after the good-through
date, does the app add an estimate of extra interest:

  extra days     = closing date - good-through date (calendar days)
  extra interest = extra days x daily interest

The lender's final payoff statement controls; this is always shown as an
estimate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from ..money import fmt, round_cents


@dataclass
class PayoffResult:
    amount: Decimal | None
    extra_interest: Decimal = Decimal("0")
    steps: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    interest_estimated: bool = False


def calculate_payoff(
    payoff_amount: Decimal | None,
    good_through: date | None,
    per_diem: Decimal | None,
    closing_date: date | None,
) -> PayoffResult:
    if payoff_amount is None:
        return PayoffResult(None, flags=["Payoff amount not entered."])

    steps = [f"Payoff amount entered: {fmt(payoff_amount)}"]
    flags: list[str] = []
    if good_through:
        steps.append(f"Good through: {good_through:%m/%d/%Y}")

    if good_through and per_diem is not None and closing_date and closing_date > good_through:
        days = (closing_date - good_through).days
        extra = round_cents(per_diem * days)
        steps.append(
            f"Closing ({closing_date:%m/%d/%Y}) is {days} days after the good-through date: "
            f"{days} × {fmt(per_diem)}/day = {fmt(extra)} estimated extra interest"
        )
        total = round_cents(payoff_amount + extra)
        steps.append(f"Estimated payoff at closing: {fmt(payoff_amount)} + {fmt(extra)} = {fmt(total)}")
        return PayoffResult(total, extra, steps, flags, interest_estimated=True)

    if good_through and closing_date and closing_date > good_through and per_diem is None:
        flags.append(
            "Closing is after the payoff good-through date, but no daily interest was entered, "
            "so the payoff may be understated."
        )
    return PayoffResult(round_cents(payoff_amount), Decimal("0"), steps, flags)
