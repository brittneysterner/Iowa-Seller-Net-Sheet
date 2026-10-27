from datetime import date
from decimal import Decimal as D

import pytest

from netsheet import models
from netsheet.calculations import property_tax
from netsheet.calculations.commission import calculate_commission
from netsheet.calculations.net_proceeds import compute
from netsheet.calculations.payoff import calculate_payoff
from netsheet.calculations.transfer_tax import calculate_transfer_tax
from netsheet.money import MoneyError, parse_money, parse_percent


# ---------------------------------------------------------------- money parsing
@pytest.mark.parametrize("text,expected", [
    ("250000", D("250000")), ("$250,000", D("250000")), ("250,000.50", D("250000.50")),
    (" $1,234.5 ", D("1234.5")), ("(100)", D("-100")),
])
def test_parse_money(text, expected):
    assert parse_money(text) == expected


@pytest.mark.parametrize("text", ["abc", "12.345", "1,2,3x", "NaN", "inf"])
def test_parse_money_refuses_to_guess(text):
    with pytest.raises(MoneyError):
        parse_money(text)


def test_blank_money_is_none_not_zero():
    assert parse_money("") is None
    assert parse_money("   ") is None


def test_percent_bounds():
    assert parse_percent("2.5%") == D("2.5")
    with pytest.raises(MoneyError):
        parse_percent("150")


# ---------------------------------------------------------------- transfer tax (Iowa Code 428A.1)
@pytest.mark.parametrize("price,expected", [
    ("250000", "399.20"),   # 249,500 / 500 = 499 exactly
    ("250250", "400.00"),   # 249,750 / 500 = 499.5 -> 500
    ("500", "0.00"),        # first $500 not taxed
    ("400", "0.00"),
    ("500.01", "0.80"),     # any fraction of $500 counts
    ("1000", "0.80"),
    ("1000.01", "1.60"),
    ("100000", "159.20"),
    ("189900", "303.20"),   # 189,400 / 500 = 378.8 -> 379 x .80
])
def test_transfer_tax(price, expected):
    assert calculate_transfer_tax(D(price)).amount == D(expected)


def test_transfer_tax_shows_math():
    r = calculate_transfer_tax(D("250250"))
    joined = " ".join(r.steps)
    assert "rounded up to 500" in joined and "$400.00" in joined


def test_transfer_tax_flags_are_not_decisions():
    r = calculate_transfer_tax(D("250000"), personal_property_separately_valued=True, exemption_claimed=True)
    assert r.amount == D("399.20")  # unchanged: the app does not decide these questions
    assert len(r.flags) == 2 and all(f.startswith("REVIEW") for f in r.flags)


# ---------------------------------------------------------------- commission
def test_commission_percent():
    assert calculate_commission(D("250000"), "percent", D("2.75"), None).amount == D("6875.00")


def test_commission_percent_rounds_to_cent():
    assert calculate_commission(D("199999"), "percent", D("2.5"), None).amount == D("4999.98")  # 4999.975 -> .98


def test_commission_percent_plus_flat():
    r = calculate_commission(D("200000"), "percent_plus_flat", D("3"), D("395"))
    assert r.amount == D("6395.00")


def test_commission_needs_inputs_instead_of_guessing():
    assert calculate_commission(None, "percent", D("3"), None).amount is None
    assert calculate_commission(D("1"), "flat", None, None).amount is None


# ---------------------------------------------------------------- payoff
def test_payoff_without_optional_fields():
    r = calculate_payoff(D("120000"), None, None, date(2026, 11, 1))
    assert r.amount == D("120000.00") and not r.interest_estimated


def test_payoff_adds_daily_interest_when_given():
    r = calculate_payoff(D("120000"), date(2026, 10, 20), D("18.50"), date(2026, 10, 30))
    assert r.amount == D("120185.00") and r.extra_interest == D("185.00") and r.interest_estimated


def test_payoff_warns_when_per_diem_missing():
    r = calculate_payoff(D("120000"), date(2026, 10, 20), None, date(2026, 10, 30))
    assert r.amount == D("120000.00") and r.flags


# ---------------------------------------------------------------- property tax (form ¶9)
def _auto(res):
    return {ln.key: ln.amount for ln in res.lines}


def test_fiscal_year_start():
    assert property_tax.fiscal_year_start(date(2026, 7, 1)) == 2026
    assert property_tax.fiscal_year_start(date(2027, 6, 30)) == 2026


@pytest.mark.parametrize("poss,seller,conv,days", [
    (date(2026, 7, 31), True, "360", 30),
    (date(2026, 7, 31), True, "365", 31),
    (date(2026, 10, 15), True, "360", 105),
    (date(2026, 10, 15), False, "360", 104),
    (date(2026, 8, 31), True, "360", 60),     # 31st counts as 30 under 30-day months
    (date(2027, 2, 28), True, "360", 238),    # 7 full months + 28
    (date(2026, 7, 1), True, "360", 1),
    (date(2026, 7, 1), False, "360", 0),
    (date(2027, 6, 30), True, "365", 365),
])
def test_seller_days(poss, seller, conv, days):
    assert property_tax.seller_days(poss, seller, conv)[0] == days


def test_proration_october_example():
    # Possession Oct 15, 2026; prior-year bill $4,976; new bill $4,864 issued; Sept paid, March not.
    res = property_tax.calculate_proration(date(2026, 10, 15), D("4976"), D("4864"), "paid", "unpaid")
    assert _auto(res) == {"ptax_auto_second": D("2432.00"), "ptax_auto_proration": D("1451.33")}
    assert next(ln for ln in res.lines if ln.key == "ptax_auto_second").status == "actual"
    assert not res.warnings


def test_proration_unknown_paid_status_is_charged_and_flagged():
    res = property_tax.calculate_proration(date(2026, 10, 15), D("4976"), D("4864"))
    assert sum(_auto(res).values()) == D("4864") + D("1451.33")
    assert len(res.warnings) == 2 and all(ln.status == "estimated" for ln in res.lines)


def test_proration_estimates_current_bill_when_not_issued():
    res = property_tax.calculate_proration(date(2026, 7, 31), D("4976"), None, "unpaid", "unpaid")
    a = _auto(res)
    assert a["ptax_auto_first"] == D("2488.00") and a["ptax_auto_second"] == D("2488.00")
    assert all(ln.status == "estimated" for ln in res.lines)


def test_proration_odd_cent_bill_halves_sum_exactly():
    res = property_tax.calculate_proration(date(2026, 7, 31), D("4976.01"), None, "unpaid", "unpaid")
    a = _auto(res)
    assert a["ptax_auto_first"] + a["ptax_auto_second"] == D("4976.01")


def test_proration_spring_possession_warns_if_unpaid():
    res = property_tax.calculate_proration(date(2027, 5, 10), D("4976"), D("4864"), "paid", "unpaid")
    assert not any("April and June" in w for w in res.warnings)
    res2 = property_tax.calculate_proration(date(2027, 5, 10), D("4976"), D("4864"), "unpaid", "unpaid")
    assert any("April and June" in w for w in res2.warnings)


# ---------------------------------------------------------------- full net sheet
def _tx(mode="contract"):
    tx = models.new_transaction(mode, "Test")
    tx["facts"]["sale_price"]["value"] = "250000"
    tx["facts"]["closing_date"]["value"] = "2026-10-30"
    return tx


def test_full_net_sheet():
    tx = _tx()
    tx["commissions"] = [
        {"id": "a", "role": "listing", "method": "percent", "percent": "3", "flat": "", "status": "estimated"},
        {"id": "b", "role": "admin", "method": "flat", "percent": "", "flat": "395", "status": "actual"},
    ]
    tx["payoffs"] = [{"id": "p", "lender": "ABC Bank", "amount": "100000", "good_through": "", "per_diem": "", "status": "actual"}]
    tx["property_tax"]["lines"] = [{"id": "t", "label": "Taxes", "amount": "2379.45", "kind": "debit", "status": "estimated"}]
    tx["abstract"] = {"amount": "450", "status": "estimated", "provider": "X Abstract", "notes": ""}
    tx["deed_prep"] = {"amount": "150", "status": "actual", "provider": "", "notes": ""}
    tx["other_costs"] = [{"id": "o", "label": "Home warranty", "amount": "550", "status": "estimated"}]
    tx["credits"] = [{"id": "c", "label": "Escrow refund", "amount": "100", "status": "estimated"}]
    tx["facts"]["seller_paid_buyer_costs"]["value"] = "3000"
    tx["facts"]["earnest_money"]["value"] = "5000"

    s = compute(tx)
    # 7500 + 395 + 2379.45 + 399.20 + 450 + 150 + 550 + 3000 = 14823.65
    assert s.total_debits == D("14823.65")
    assert s.total_payoffs == D("100000.00")
    assert s.total_credits == D("100.00")
    assert s.net == D("135276.35")
    # earnest money is informational only
    assert any("Earnest money" in i for i in s.info)
    assert not s.input_errors


def test_tax_needs_inputs_instead_of_guessing():
    s = compute(_tx())
    assert any("Property taxes not calculated yet" in w for w in s.warnings)
    assert not any(ln.key.startswith("ptax_auto") for ln in s.lines)


def test_tax_special_case_and_manual_mode_skip_calculation():
    tx = _tx()
    tx["property_tax"]["basis_bill"] = "4976"
    tx["property_tax"]["not_full_assessment"] = True
    s = compute(tx)
    assert not any(ln.key.startswith("ptax_auto") for ln in s.lines)
    assert any("special case" in w for w in s.warnings)
    tx["property_tax"]["not_full_assessment"] = False
    tx["property_tax"]["method"] = "manual"
    assert not any(ln.key.startswith("ptax_auto") for ln in compute(tx).lines)


def test_tax_uses_closing_date_when_no_possession_date():
    tx = _tx()  # closing 2026-10-30, no possession date
    tx["property_tax"].update(basis_bill="3600", first_paid="paid", second_paid="paid")
    s = compute(tx)
    pr = next(ln for ln in s.lines if ln.key == "ptax_auto_proration")
    assert pr.amount == D("1200.00")  # 3600 x (3x30 + 30) / 360
    assert any("closing date was used" in i for i in s.info)


def test_blank_amounts_are_excluded_and_warned_not_guessed():
    s = compute(_tx())
    abstract = next(ln for ln in s.lines if ln.key == "abstract")
    assert abstract.amount is None
    assert any("Abstract continuation: no amount" in w for w in s.warnings)
    assert any("No property-tax amount" in w for w in s.warnings)
    assert s.net == D("250000") - D("399.20")


def test_invalid_input_is_reported():
    tx = _tx()
    tx["other_costs"] = [{"id": "o", "label": "Repairs", "amount": "abc", "status": "estimated"}]
    s = compute(tx)
    assert s.input_errors and s.warnings[0].startswith("INPUT PROBLEM")


def test_estimated_never_shown_as_actual():
    tx = _tx()
    tx["payoffs"] = [{"id": "p", "lender": "L", "amount": "1000", "good_through": "2026-10-20", "per_diem": "5", "status": "actual"}]
    s = compute(tx)
    payoff = next(ln for ln in s.lines if ln.key == "payoff:p")
    assert payoff.status == "estimated"  # added interest makes it an estimate even if marked actual
    tt = next(ln for ln in s.lines if ln.key == "transfer_tax")
    assert tt.status == "estimated"


def test_actual_transfer_tax_override_flags_difference():
    tx = _tx()
    tx["transfer_tax"]["actual_amount"] = "400.00"
    s = compute(tx)
    tt = next(ln for ln in s.lines if ln.key == "transfer_tax")
    assert tt.amount == D("400.00") and tt.status == "actual"
    assert any("differs" in f for f in tt.flags)


def test_unconfirmed_contract_fact_is_flagged():
    tx = _tx()
    tx["facts"]["sale_price"].update(source="contract", confirmed=False, page=1, quote="$250,000")
    s = compute(tx)
    assert any("NEEDS REVIEW" in w and "Purchase price" in w for w in s.warnings)


def test_listing_mode_without_closing_date_is_info_not_warning():
    tx = models.new_transaction("listing", "L")
    tx["facts"]["sale_price"]["value"] = "300000"
    s = compute(tx)
    assert any("closing date" in i for i in s.info)
    assert not any(w.startswith("No closing date") for w in s.warnings)
