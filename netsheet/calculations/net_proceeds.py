"""Assemble the seller net sheet from a saved transaction record.

    Purchase price
  − seller expenses / debits
  − mortgage & lien payoffs
  + seller credits
  = ESTIMATED NET PROCEEDS TO SELLER

This function is pure: the same record always produces the same result. It
never invents a number. A blank amount is left out of the totals and reported
as a warning, never filled with a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .. import models
from ..money import MoneyError, fmt, parse_money, parse_percent, round_cents
from . import property_tax
from .commission import calculate_commission
from .payoff import calculate_payoff
from .transfer_tax import SOURCE as TT_SOURCE
from .transfer_tax import calculate_transfer_tax

SECTIONS = [
    ("compensation", "Real Estate Compensation"),
    ("payoffs", "Mortgage & Lien Payoffs"),
    ("taxes", "Taxes"),
    ("title", "Abstract, Deed & Closing"),
    ("other", "Other Seller Costs"),
    ("concessions", "Seller Concessions to Buyer"),
    ("credits", "Credits to Seller"),
]
SECTION_NAMES = dict(SECTIONS)


@dataclass
class Line:
    key: str
    section: str
    label: str
    amount: Decimal | None
    kind: str  # "debit" (reduces seller net) or "credit" (increases it)
    status: str  # "estimated" or "actual"
    source: str
    provider: str = ""
    notes: str = ""
    steps: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    @property
    def is_estimated(self) -> bool:
        return self.status != "actual"

    @property
    def signed(self) -> Decimal:
        if self.amount is None:
            return Decimal("0")
        return -self.amount if self.kind == "debit" else self.amount


@dataclass
class NetSheet:
    mode: str
    facts: dict
    price: Decimal | None
    lines: list[Line]
    total_debits: Decimal
    total_payoffs: Decimal
    total_credits: Decimal
    net: Decimal | None
    warnings: list[str]
    info: list[str]
    input_errors: list[str]
    tax_pending_message: str

    def section_lines(self, section: str) -> list[Line]:
        return [ln for ln in self.lines if ln.section == section]

    @property
    def sections(self):
        return [(key, name, self.section_lines(key)) for key, name in SECTIONS if self.section_lines(key)]

    @property
    def has_estimates(self) -> bool:
        return any(ln.is_estimated for ln in self.lines if ln.amount is not None)


def _money(text, what: str, errors: list[str]) -> Decimal | None:
    try:
        return parse_money(text)
    except MoneyError as exc:
        errors.append(f"{what}: {exc}")
        return None


def _status(value: str) -> str:
    return "actual" if value == "actual" else "estimated"


def _source_for_fact(fact: dict) -> str:
    if fact.get("source") == "contract":
        page = f", page {fact['page']}" if fact.get("page") else ""
        state = "confirmed by agent" if fact.get("confirmed") else "NOT YET CONFIRMED"
        return f"Purchase Agreement{page} ({state})"
    return "Entered by agent"


def compute(tx: dict) -> NetSheet:
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []
    lines: list[Line] = []
    facts = tx["facts"]

    price = _money(facts["sale_price"]["value"], "Purchase price", errors)
    try:
        closing = models.parse_date(facts["closing_date"]["value"])
    except ValueError as exc:
        errors.append(f"Closing date: {exc}")
        closing = None
    try:
        possession = models.parse_date(facts["possession_date"]["value"])
    except ValueError as exc:
        errors.append(f"Possession date: {exc}")
        possession = None

    is_listing = tx["mode"] == "listing"
    if price is None:
        warnings.append(
            "No hypothetical sale price entered." if is_listing else "No purchase price entered."
        )
    if closing is None:
        (info if is_listing else warnings).append("No closing date entered.")
    if closing and possession and closing != possession:
        info.append(
            f"Possession date ({possession:%m/%d/%Y}) differs from closing date ({closing:%m/%d/%Y}). "
            "Check how the Purchase Agreement ties prorations and possession to these dates."
        )

    # Contract facts that came from the document must be confirmed by the agent.
    for key, (label, _kind) in models.FACTS.items():
        fact = facts.get(key) or {}
        if fact.get("source") == "contract" and not fact.get("confirmed"):
            warnings.append(f"NEEDS REVIEW: '{label}' was read from the contract and has not been confirmed.")
    for item in tx.get("review_items", []):
        if not item.get("resolved"):
            warnings.append(f"NEEDS REVIEW: {item.get('text') or 'Contract provision flagged for review'}")

    # --- Real estate compensation -------------------------------------------------
    for c in tx.get("commissions", []):
        role_label = models.COMMISSION_ROLES.get(c.get("role"), "Compensation")
        label = c.get("label") or role_label
        pct = None
        try:
            pct = parse_percent(c.get("percent"))
        except MoneyError as exc:
            errors.append(f"{label}: {exc}")
        flat = _money(c.get("flat"), label, errors)
        res = calculate_commission(price, c.get("method", "percent"), pct, flat)
        ln = Line(
            key=f"commission:{c['id']}", section="compensation", label=label, amount=res.amount,
            kind="debit", status=_status(c.get("status")), source="Calculated from terms entered by agent",
            provider=c.get("payee", ""), notes=c.get("notes", ""), steps=res.steps,
        )
        for p in res.problems:
            ln.flags.append(p)
            warnings.append(f"{label}: {p} (not included in totals)")
        lines.append(ln)
    if not tx.get("commissions"):
        info.append("No real estate compensation lines entered.")

    # --- Payoffs ------------------------------------------------------------------
    for p in tx.get("payoffs", []):
        label = p.get("lender") or "Mortgage / lien payoff"
        amt = _money(p.get("amount"), label, errors)
        per_diem = _money(p.get("per_diem"), f"{label} daily interest", errors)
        try:
            good = models.parse_date(p.get("good_through"))
        except ValueError as exc:
            errors.append(f"{label} good-through date: {exc}")
            good = None
        res = calculate_payoff(amt, good, per_diem, closing)
        status = _status(p.get("status"))
        if res.interest_estimated:
            status = "estimated"  # added interest is always an estimate
        ln = Line(
            key=f"payoff:{p['id']}", section="payoffs", label=label, amount=res.amount, kind="debit",
            status=status, source="Entered by agent" + (" + calculated daily interest" if res.interest_estimated else ""),
            notes=p.get("notes", ""), steps=res.steps, flags=res.flags,
        )
        for f in res.flags:
            warnings.append(f"{label}: {f}")
        lines.append(ln)

    # --- Property taxes (manual only; proration calculation pending) ---------------
    pt = tx.get("property_tax", {})
    for t in pt.get("lines", []):
        label = t.get("label") or "Property taxes"
        amt = _money(t.get("amount"), label, errors)
        kind = "credit" if t.get("kind") == "credit" else "debit"
        ln = Line(
            key=f"ptax:{t['id']}", section="taxes", label=label, amount=amt, kind=kind,
            status=_status(t.get("status")),
            source="Entered manually by agent — NOT calculated by this app",
            notes=t.get("notes", ""),
            steps=["Amount entered manually. Property-tax proration calculation is pending approval."],
        )
        if amt is None:
            warnings.append(f"{label}: no amount entered (not included in totals).")
        lines.append(ln)
    if not any(_money(t.get("amount"), "", []) is not None for t in pt.get("lines", [])):
        warnings.append(
            "No property-tax amount entered. In Iowa the seller usually owes taxes at closing, so this "
            "net is likely OVERSTATED until property taxes are added."
        )

    # --- Transfer tax -------------------------------------------------------------
    tt = tx.get("transfer_tax", {})
    if tt.get("include", True):
        actual = _money(tt.get("actual_amount"), "Transfer tax actual amount", errors)
        if price is not None:
            res = calculate_transfer_tax(
                price,
                personal_property_separately_valued=bool(tt.get("personal_property_flag")),
                exemption_claimed=bool(tt.get("exemption_flag")),
            )
            steps = list(res.steps)
            if actual is not None:
                steps.append(f"Actual amount entered from settlement figures: {fmt(actual)} (used in totals)")
                if actual != res.amount:
                    res.flags.append(
                        f"Actual transfer tax {fmt(actual)} differs from the calculated {fmt(res.amount)}. Review."
                    )
            lines.append(Line(
                key="transfer_tax", section="taxes", label="Iowa real estate transfer tax",
                amount=actual if actual is not None else res.amount, kind="debit",
                status="actual" if actual is not None else "estimated",
                source=("Actual amount entered by agent" if actual is not None else f"Calculated by app — {TT_SOURCE}"),
                notes=tt.get("notes", ""), steps=steps, flags=res.flags,
            ))
            warnings.extend(res.flags)
        else:
            lines.append(Line(
                key="transfer_tax", section="taxes", label="Iowa real estate transfer tax", amount=actual,
                kind="debit", status="actual" if actual is not None else "estimated",
                source="Cannot calculate without a sale price", flags=["Enter a sale price."],
            ))

    # --- Abstract continuation & deed preparation ---------------------------------
    for key, label in (("abstract", "Abstract continuation"), ("deed_prep", "Deed preparation")):
        item = tx.get(key, {})
        amt = _money(item.get("amount"), label, errors)
        if amt is None:
            warnings.append(f"{label}: no amount entered (not included in totals).")
        lines.append(Line(
            key=key, section="title", label=label, amount=amt, kind="debit",
            status=_status(item.get("status")), source="Entered by agent",
            provider=item.get("provider", ""), notes=item.get("notes", ""),
        ))

    # --- Other seller costs -------------------------------------------------------
    for o in tx.get("other_costs", []):
        label = o.get("label") or "Other seller expense"
        amt = _money(o.get("amount"), label, errors)
        if amt is None:
            warnings.append(f"{label}: no amount entered (not included in totals).")
        section = "title" if label.lower().startswith(("settlement", "recording")) else "other"
        lines.append(Line(
            key=f"other:{o['id']}", section=section, label=label, amount=amt, kind="debit",
            status=_status(o.get("status")), source="Entered by agent",
            provider=o.get("provider", ""), notes=o.get("notes", ""),
        ))

    # --- Seller concessions from the contract -------------------------------------
    spbc = facts.get("seller_paid_buyer_costs", {})
    spbc_amt = _money(spbc.get("value"), "Seller-paid buyer closing costs", errors)
    if spbc_amt is not None:
        lines.append(Line(
            key="seller_paid_buyer_costs", section="concessions",
            label="Seller-paid buyer closing costs / credit", amount=spbc_amt, kind="debit",
            status=_status(tx.get("seller_paid_buyer_costs_status")), source=_source_for_fact(spbc),
            flags=["If the contract says 'up to' this amount, the actual credit may be lower."],
        ))

    # --- Credits to seller --------------------------------------------------------
    for c in tx.get("credits", []):
        label = c.get("label") or "Credit to seller"
        amt = _money(c.get("amount"), label, errors)
        if amt is None:
            warnings.append(f"{label}: no amount entered (not included in totals).")
        lines.append(Line(
            key=f"credit:{c['id']}", section="credits", label=label, amount=amt, kind="credit",
            status=_status(c.get("status")), source="Entered by agent", notes=c.get("notes", ""),
        ))

    # --- Earnest money is informational only ----------------------------------------
    em = _money(facts.get("earnest_money", {}).get("value"), "Earnest money", errors)
    if em is not None:
        info.append(
            f"Earnest money of {fmt(em)} is part of the purchase price (applied toward it at closing). "
            "It does not change the seller's net and is not subtracted again."
        )

    for e in errors:
        warnings.insert(0, f"INPUT PROBLEM — {e}")

    total_payoffs = round_cents(sum((ln.amount for ln in lines if ln.section == "payoffs" and ln.amount is not None), Decimal("0")))
    total_debits = round_cents(sum((ln.amount for ln in lines if ln.kind == "debit" and ln.section != "payoffs" and ln.amount is not None), Decimal("0")))
    total_credits = round_cents(sum((ln.amount for ln in lines if ln.kind == "credit" and ln.amount is not None), Decimal("0")))
    net = None if price is None else round_cents(price - total_debits - total_payoffs + total_credits)

    return NetSheet(
        mode=tx["mode"], facts=facts, price=price, lines=lines, total_debits=total_debits,
        total_payoffs=total_payoffs, total_credits=total_credits, net=net, warnings=warnings,
        info=info, input_errors=errors, tax_pending_message=property_tax.PENDING_MESSAGE,
    )
