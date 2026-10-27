"""Regression checks against real closed transactions (names, addresses and file numbers removed).

Closed transaction #1 — Cerro Gordo County, settled 2026-07-31, final HUD-1 settlement statement.
Seller side: line 603 cash to seller $359,581.06.
"""

from decimal import Decimal as D

from netsheet import models
from netsheet.calculations.net_proceeds import compute
from netsheet.calculations.transfer_tax import calculate_transfer_tax


def _closed_1():
    tx = models.new_transaction("contract", "closed-1")
    f = tx["facts"]
    f["sale_price"]["value"] = "610000"
    f["closing_date"]["value"] = "2026-07-31"
    f["possession_date"]["value"] = "2026-07-31"
    f["earnest_money"]["value"] = "1000"
    # HUD 700/703/506: 5% = $30,500; $1,000 deposit retained by broker + $29,500 paid at settlement
    tx["commissions"] = [{"id": "c1", "role": "listing", "method": "percent", "percent": "5", "flat": "", "status": "actual"}]
    tx["payoffs"] = [{"id": "p1", "lender": "First mortgage", "amount": "212716.06", "good_through": "", "per_diem": "", "status": "actual"}]
    # HUD 511: County taxes 07/01/25 to 07/31/26 (entered manually; proration method still pending)
    tx["property_tax"]["lines"] = [{"id": "t1", "label": "County taxes", "amount": "5390.68", "kind": "debit", "status": "actual"}]
    tx["abstract"] = {"amount": "430", "status": "actual", "provider": "", "notes": ""}      # HUD 1102
    tx["deed_prep"] = {"amount": "360", "status": "actual", "provider": "", "notes": ""}     # HUD 1105
    tx["other_costs"] = [
        {"id": "o1", "label": "Courier fee", "amount": "40", "status": "actual"},          # HUD 1104
        {"id": "o2", "label": "File affidavits", "amount": "7", "status": "actual"},       # HUD 1205
    ]
    return tx


def test_closed_1_transfer_tax_matches_revenue_stamps():
    assert calculate_transfer_tax(D("610000")).amount == D("975.20")  # HUD 1202


def test_closed_1_net_matches_settlement_statement():
    s = compute(_closed_1())
    assert s.total_debits == D("37702.88")  # HUD 1400 seller $31,312.20 + $1,000 retained + $5,390.68 taxes
    assert s.total_payoffs == D("212716.06")
    assert s.net == D("359581.06")  # HUD 603
