"""The saved record for one net sheet ("transaction").

Everything is stored as plain JSON text so it can be read without this app.
Money is stored as exact decimal text (e.g. "250000.00"), never as a float.

Every transaction fact keeps its PROVENANCE — where the value came from:
  source   "manual"   typed by the agent
           "contract" suggested from the Purchase Agreement (future AI step)
  page     page number in the Purchase Agreement (contract source only)
  quote    the exact contract wording the value came from
  confirmed  True once the agent has reviewed and approved it
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

SCHEMA_VERSION = 1

MODES = {
    "listing": "Listing Appointment (no contract)",
    "contract": "Under Contract (Purchase Agreement)",
}

STATUSES = {"estimated": "Estimated", "actual": "Actual"}

# key: (label, kind) — kind is "text", "money", "date" or "longtext"
FACTS: dict[str, tuple[str, str]] = {
    "property_address": ("Property address", "text"),
    "sellers": ("Seller(s)", "text"),
    "buyers": ("Buyer(s)", "text"),
    "sale_price": ("Purchase price", "money"),
    "closing_date": ("Closing date", "date"),
    "possession_date": ("Possession date", "date"),
    "earnest_money": ("Earnest money", "money"),
    "seller_paid_buyer_costs": ("Seller-paid buyer closing costs / credit", "money"),
    "other_concessions": ("Other financial concessions", "longtext"),
    "personal_property": ("Personal property included / excluded", "longtext"),
    "unusual_provisions": ("Unusual financial provisions", "longtext"),
    # Who handles the closing matters: tax-proration conventions differ between
    # attorneys, escrow/title companies (e.g. Escrow Plus) and lenders.
    "settlement_agent": ("Settlement agent / closing attorney", "text"),
}

# Facts that only make sense once a Purchase Agreement exists.
CONTRACT_ONLY_FACTS = {"buyers", "earnest_money"}

COMMISSION_ROLES = {
    "listing": "Listing brokerage compensation",
    "buyer": "Seller-paid buyer brokerage compensation",
    "admin": "Brokerage / administrative fee",
    "other": "Other compensation",
}

# Short reminders shown under a field, from the Iowa Association of REALTORS(R)
# "Iowa Offer to Purchase Real Estate" (form updated 3/10/2026). Contract mode only.
FACT_HINTS = {
    "closing_date": "Form ¶4: closing is “on or before” this date, so the actual date may be earlier.",
    "possession_date": "Form ¶4: possession is at closing unless the parties agree otherwise. "
                       "Form ¶9 ties tax and other prorations to the POSSESSION date.",
    "seller_paid_buyer_costs": "The form has no printed blank for this. Look in ¶5 “OTHER”, ¶29 and any addenda.",
    "settlement_agent": "e.g. Escrow Plus, the lender, or a closing attorney. Tax-proration methods can differ between them.",
    "personal_property": "Form ¶8: personal property passes only by a separate bill of sale.",
}

# Suggestions offered for optional seller costs. None are added automatically.
OTHER_COST_SUGGESTIONS = [
    "Settlement / closing fee",
    "Recording fees (release of mortgage, etc.)",
    "Special assessments",
    "Escrow holdback for pending / deficiency assessments",
    "Septic time-of-transfer inspection",
    "Unpaid utilities (water / sewer)",
    "Seller-paid repairs",
    "Wood pest inspection / treatment",
    "Home warranty",
    "Wire / courier fees",
    "HOA dues / transfer fee",
    "Rent / security deposits to buyer",
    "Other seller expense",
]

CREDIT_SUGGESTIONS = [
    "Unused fuel / propane (at current market value)",
    "Prepaid HOA dues refund",
    "Escrow / utility deposit refund",
    "Other credit to seller",
]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def blank_fact() -> dict:
    return {"value": "", "source": "manual", "page": None, "quote": None, "confirmed": True, "updated_at": None}


def blank_line(**extra) -> dict:
    line = {"id": new_id(), "label": "", "amount": "", "status": "estimated", "provider": "", "notes": ""}
    line.update(extra)
    return line


def new_transaction(mode: str, folder_name: str) -> dict:
    if mode not in MODES:
        raise ValueError(f"Unknown mode {mode}")
    ts = now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "id": folder_name,
        "mode": mode,
        "created_at": ts,
        "updated_at": ts,
        "facts": {k: blank_fact() for k in FACTS},
        "seller_paid_buyer_costs_status": "estimated",
        "review_items": [],
        "commissions": [],
        "payoffs": [],
        "property_tax": {
            "county": "",
            "parcel": "",
            "annual_net_tax": "",
            "tax_source": "",
            "tax_retrieved": "",
            "notes": "",
            "lines": [],
        },
        "transfer_tax": {
            "include": True,
            "personal_property_flag": False,
            "exemption_flag": False,
            "actual_amount": "",
            "notes": "",
        },
        "abstract": {"amount": "", "status": "estimated", "provider": "", "notes": ""},
        "deed_prep": {"amount": "", "status": "estimated", "provider": "", "notes": ""},
        "other_costs": [],
        "credits": [],
        "contract_file": None,
        "comparison": {"line_amounts": {}, "settlement_net": "", "notes": ""},
    }


def parse_date(text: str | None) -> date | None:
    """Accepts 2026-10-15 (what browsers send) or 10/15/2026. Blank -> None."""
    if not text:
        return None
    text = text.strip()
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"'{text}' is not a date (use MM/DD/YYYY)")
