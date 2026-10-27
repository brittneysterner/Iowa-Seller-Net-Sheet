"""Iowa property-tax proration — ESTIMATE, per the Iowa Association of REALTORS(R)
"Iowa Offer to Purchase Real Estate" (form updated 3/10/2026), paragraph 9.

Approved by the agent on 2026-10-27 to be built from the evidence available:
  * the form's ¶9 wording (docs/PURCHASE-AGREEMENT-REVIEW.md),
  * closed transaction #1, an attorney closing (docs/VALIDATION-CLOSED-TRANSACTION-1.md),
  * the 360-day year / 30-day month convention common in licensing courses.
Settlement agents (attorneys, Escrow Plus, lenders) may calculate slightly
differently, so every result is labeled an estimate.

METHOD
  Possession fiscal year (FY) = the July 1 – June 30 year containing the
  possession date (closing date if no possession date was entered; form ¶4).
  Say possession is in FY Y-(Y+1), i.e. on or after July 1 of year Y.

  Part A — ¶9 "taxes due and payable in the fiscal year in which possession is
  given": the tax bill payable Sept Y / March Y+1. The seller is charged each
  installment of that bill not yet paid. If that bill has not been entered (the
  county usually issues it in August), it is estimated from the basis bill.

  Part B — ¶9 proration "for the fiscal year in which possession is given",
  July 1 Y through the possession date, on the basis of "the taxes that were
  certified and payable in the prior fiscal year": the bill payable Sept Y-1 /
  March Y.
      360 convention (default): days = 30 per full month + day of month (max 30)
      365 convention:           days = actual calendar days
      amount = basis bill x days / 360 (or 365)
  Possession day counted as the seller's by default (setting).

  ¶9 special case — taxes not based on a full assessment of present
  improvements (e.g. new construction): NOT calculated; the agent must enter
  the amount manually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from ..money import fmt, round_cents

METHOD_NAME = "Iowa REALTORS® form ¶9 (prior-year bill; 360-day year unless changed)"

DISCLAIMER = (
    "Property taxes are an ESTIMATE using your Purchase Agreement's ¶9 with the prior-year tax bill and a "
    "360-day year (30-day months) unless you changed that setting. Closing agents may calculate slightly "
    "differently (for example, by actual days)."
)

PAID_CHOICES = {"unknown": "Not sure", "paid": "Paid", "unpaid": "Not paid"}


@dataclass
class TaxLine:
    key: str
    label: str
    amount: Decimal
    status: str  # "estimated" or "actual"
    steps: list[str] = field(default_factory=list)


@dataclass
class ProrationResult:
    lines: list[TaxLine] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    fiscal_year_start: int | None = None


def fiscal_year_start(d: date) -> int:
    """Calendar year in which the July 1 – June 30 fiscal year containing d begins."""
    return d.year if d.month >= 7 else d.year - 1


def fy_label(start: int) -> str:
    return f"{start}-{str(start + 1)[2:]}"


def bill_labels(possession: date | None) -> dict:
    """Plain-English names for the two tax bills, for the input screen."""
    if possession is None:
        return {
            "basis": "Prior-year tax bill (annual total)",
            "current": "Current-year tax bill (annual total), if already issued",
            "first": "First installment (September)",
            "second": "Second installment (March)",
        }
    y = fiscal_year_start(possession)
    return {
        "basis": f"Tax bill paid Sept {y - 1} and March {y} (annual total)",
        "current": f"Tax bill due Sept {y} and March {y + 1} (annual total), if already issued",
        "first": f"September {y} installment",
        "second": f"March {y + 1} installment",
    }


def seller_days(possession: date, possession_day_to_seller: bool, convention: str) -> tuple[int, str]:
    """Days of the possession fiscal year charged to the seller, and how they were counted."""
    start = date(fiscal_year_start(possession), 7, 1)
    end = possession if possession_day_to_seller else possession - timedelta(days=1)
    if end < start:
        return 0, "Possession on July 1 with the possession day going to the buyer: 0 seller days."
    if convention == "365":
        days = (end - start).days + 1
        return days, f"July 1, {start.year} through {end:%B %-d, %Y} = {days} actual days"
    full_months = (end.year - start.year) * 12 + (end.month - start.month)
    day_part = min(end.day, 30)
    days = full_months * 30 + day_part
    if full_months:
        how = f"{full_months} full month(s) × 30 = {full_months * 30} days, plus {day_part} day(s) of {end:%B}"
    else:
        how = f"{day_part} day(s) of {end:%B}"
    return days, f"July 1, {start.year} through {end:%B %-d, %Y}: {how} = {days} days (30-day months)"


def _halves(annual: Decimal) -> tuple[Decimal, Decimal]:
    first = round_cents(annual / 2)
    return first, annual - first


def calculate_proration(
    possession: date,
    basis_bill: Decimal,
    current_bill: Decimal | None = None,
    first_paid: str = "unknown",
    second_paid: str = "unknown",
    convention: str = "360",
    possession_day_to_seller: bool = True,
    possession_is_closing_date: bool = False,
) -> ProrationResult:
    res = ProrationResult()
    y = fiscal_year_start(possession)
    res.fiscal_year_start = y
    divisor = Decimal(365) if convention == "365" else Decimal(360)
    labels = bill_labels(possession)

    if possession_is_closing_date:
        res.info.append("No possession date entered, so the closing date was used (form ¶4: possession at closing).")

    # ---- Part A: installments of the bill payable in the possession fiscal year
    if current_bill is not None:
        source_note = f"{labels['current'].split(' (')[0]}: {fmt(current_bill)} (entered from the county)"
        bill, bill_status = current_bill, "actual"
    else:
        source_note = (
            f"{labels['current'].split(' (')[0]} not entered (usually issued in August), so it is ESTIMATED "
            f"from the prior-year bill of {fmt(basis_bill)}"
        )
        bill, bill_status = basis_bill, "estimated"
    halves = _halves(bill)
    for idx, (key, paid) in enumerate((("first", first_paid), ("second", second_paid))):
        name = labels[key]
        if paid == "paid":
            res.info.append(f"{name} marked as paid by the seller, so it is not charged again.")
            continue
        steps = [
            "Form ¶9: the seller pays all regular taxes due and payable in the fiscal year of possession "
            f"(FY {fy_label(y)}).",
            source_note,
            f"Half of {fmt(bill)} = {fmt(halves[idx])}",
        ]
        status = bill_status
        if paid == "unknown":
            status = "estimated"
            steps.append("Paid status not confirmed; charged to the seller to be safe.")
            res.warnings.append(f"Confirm whether the {name} has been paid. It is charged to the seller until confirmed.")
        res.lines.append(TaxLine(f"ptax_auto_{key}", f"Property taxes — {name}", halves[idx], status, steps))

    if possession.month in (4, 5, 6) and "paid" not in (first_paid, second_paid):
        res.warnings.append(
            "Possession is between April and June, when both installments are normally already paid. "
            "Check for delinquent taxes, which may also carry interest."
        )

    # ---- Part B: proration July 1 → possession on the prior-year (basis) bill
    days, how = seller_days(possession, possession_day_to_seller, convention)
    amount = round_cents(basis_bill * days / divisor)
    steps = [
        f"Form ¶9: taxes for FY {fy_label(y)} are prorated as of the possession date, based on the taxes "
        "certified and payable in the prior fiscal year.",
        f"Basis: {labels['basis'].split(' (')[0]} = {fmt(basis_bill)}",
        how + (" (possession day counted as the seller's)" if possession_day_to_seller
               else " (possession day counted as the buyer's)"),
        f"{fmt(basis_bill)} × {days} ÷ {divisor} = {fmt(amount)}",
    ]
    if days:
        res.lines.append(TaxLine(
            "ptax_auto_proration",
            f"Property taxes — proration July 1, {y} to possession",
            amount, "estimated", steps,
        ))
    res.info.append(
        "Tax bills reflect the seller's own credits and exemptions (e.g. homestead). The 2026 law SF 2472 "
        "changes the homestead credit to an exemption starting with taxes paid Sept 2027."
    )
    return res
