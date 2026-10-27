# Calculations and sources

All calculations are fixed code rules, written out below, with automated self-checks (`tests/`).
AI never does the math. All money uses exact decimal arithmetic. Each line is rounded to the cent
("round half up"). **A blank amount is left out of the totals and shown as a warning. It is never guessed.**

## Net proceeds

```
  Purchase price (or hypothetical sale price)
− seller expenses (compensation, taxes, abstract, deed, other costs, concessions)
− mortgage / lien payoffs
+ credits to seller
= ESTIMATED NET PROCEEDS TO SELLER
```

Earnest money is shown for information only. It's part of the purchase price, so it's not subtracted again.

## Iowa real estate transfer tax — VERIFIED

- **Source:** Iowa Code §428A.1 — <https://www.legis.iowa.gov/docs/code/428A.1.pdf>.
  The rate has been $0.80 per $500 since July 1, 1991. No change found in the 2025 or 2026 legislative sessions
  (checked 2026-10-03). The seller ("grantor") is liable for the tax.
- **Formula:** (price − $500) ÷ $500, **rounded up** to a whole number, × $0.80.
- **Examples:** $250,000 → 499 × $0.80 = **$399.20**. $250,250 → 499.5, rounded up to 500 → **$400.00**.
- **Not decided by the app (flagged for review instead):**
  - whether separately valued personal property should come out of the price
  - whether an exemption under Iowa Code §428A.2 applies
- If you enter the actual amount from the settlement statement, the app uses it, marks it ACTUAL,
  and warns you if it differs from the calculated figure.

## Real estate compensation

No default rate. Each line is a percentage of the price, a flat amount, or both. Example: $250,000 × 2.5% = $6,250.00.

## Mortgage / lien payoffs

You enter the payoff amount. Only when you *also* enter a good-through date and a daily interest amount,
and closing is after the good-through date, does the app add:
`(closing date − good-through date) in days × daily interest`.
That line is then always marked ESTIMATED. The lender's final payoff statement controls.

## Iowa property-tax proration — PENDING (not calculated)

Iowa proration is governed by the wording of the Purchase Agreement. Per your instruction, the app
does **not** calculate it until:

1. we review the Purchase Agreement form you use,
2. we test the method against a closed transaction's final settlement statement, and
3. you approve the method.

Until then, you type in the property-tax amount(s). They are labeled "entered manually — not calculated by this app."

Different settlement agents (closing attorneys, Escrow Plus, lenders) may prorate differently, so each net sheet
records who the settlement agent is. Closed transaction #1 (an attorney closing) matched "13 whole months at the
prior-year bill"; see [VALIDATION-CLOSED-TRANSACTION-1.md](VALIDATION-CLOSED-TRANSACTION-1.md).

Step 1 is done: see [PURCHASE-AGREEMENT-REVIEW.md](PURCHASE-AGREEMENT-REVIEW.md) for the form's exact ¶9 wording
and the two possible readings of "prior fiscal year." Steps 2 and 3 are still open.

Questions to settle during that review:
- ~~Closing date or possession date?~~ **Possession date** (form ¶9).
- Is the closing day a seller day or a buyer day?
- Is the daily rate based on a 365-day year or the actual number of days?
- Which tax amount is used: "last known actual net taxes," or something else?
- How are unpaid September and March installments handled?
- How are the seller's homestead, military, or other exemptions treated? This includes the 2026 change
  (SF 2472) that replaces the homestead credit with a homestead exemption, starting with taxes paid in September 2027.

## Audit trail

Every transaction fact records where it came from: *Entered by agent*, or, in the future, *Purchase
Agreement page X, with the exact wording*, which needs your confirmation before it's trusted.
Every save is recorded in `audit-log.jsonl` with the old and new values.
