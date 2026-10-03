"""Iowa real estate transfer tax.

SOURCE (verified 2026-10-03):
  Iowa Code section 428A.1 — "eighty cents for each five hundred dollars or
  fractional part of five hundred dollars in excess of five hundred dollars"
  of consideration, where consideration is the full actual sale price of the
  real property, including any encumbrance assumed by the buyer.
  Rate in effect since July 1, 1991. The grantor (seller) is liable for the tax.
  https://www.legis.iowa.gov/docs/code/428A.1.pdf

FORMULA:
  taxable amount = consideration - $500
  increments     = taxable amount / $500, rounded UP to a whole number
  tax            = increments x $0.80

This module only does arithmetic. It deliberately does NOT decide legal
questions such as whether separately valued personal property reduces the
consideration, or whether an exemption under Iowa Code 428A.2 applies. Those
situations are returned as review flags for the agent / closing attorney.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_CEILING, Decimal

from ..money import fmt

RATE_PER_INCREMENT = Decimal("0.80")
INCREMENT = Decimal("500")
EXEMPT_FIRST = Decimal("500")
SOURCE = "Iowa Code §428A.1 (rate effective July 1, 1991; verified 2026-10-03)"
SOURCE_URL = "https://www.legis.iowa.gov/docs/code/428A.1.pdf"


@dataclass
class TransferTaxResult:
    consideration: Decimal
    amount: Decimal
    steps: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


def calculate_transfer_tax(
    consideration: Decimal,
    personal_property_separately_valued: bool = False,
    exemption_claimed: bool = False,
) -> TransferTaxResult:
    if consideration is None:
        raise ValueError("A sale price is required to calculate transfer tax")
    if consideration < 0:
        raise ValueError("Sale price cannot be negative")

    steps = [f"Consideration used: {fmt(consideration)} (the sale price you entered)"]
    flags: list[str] = []

    if consideration <= EXEMPT_FIRST:
        steps.append(f"Consideration is {fmt(EXEMPT_FIRST)} or less, so no tax applies.")
        amount = Decimal("0.00")
    else:
        taxable = consideration - EXEMPT_FIRST
        raw = taxable / INCREMENT
        increments = raw.to_integral_value(rounding=ROUND_CEILING)
        amount = (increments * RATE_PER_INCREMENT).quantize(Decimal("0.01"))
        steps.append(f"Subtract the first {fmt(EXEMPT_FIRST)}: {fmt(consideration)} − {fmt(EXEMPT_FIRST)} = {fmt(taxable)}")
        if raw == increments:
            steps.append(f"Divide by $500: {fmt(taxable)} ÷ $500 = {increments} increments")
        else:
            steps.append(
                f"Divide by $500: {fmt(taxable)} ÷ $500 = {raw.normalize():f}, "
                f"rounded up to {increments} (any part of $500 counts as a full increment)"
            )
        steps.append(f"Multiply by $0.80: {increments} × $0.80 = {fmt(amount)}")

    if personal_property_separately_valued:
        flags.append(
            "REVIEW: The contract assigns a separate value to personal property. This app "
            "calculated transfer tax on the full sale price and has NOT decided whether that "
            "value should be excluded. Confirm with the closing attorney."
        )
    if exemption_claimed:
        flags.append(
            "REVIEW: You marked that an exemption from transfer tax may apply (Iowa Code 428A.2). "
            "The app has NOT applied any exemption. Confirm with the closing attorney."
        )
    return TransferTaxResult(consideration=consideration, amount=amount, steps=steps, flags=flags)
