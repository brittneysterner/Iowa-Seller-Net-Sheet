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

## Iowa property-tax proration — ESTIMATE (built 2026-10-27 at the agent's request)

Built from the evidence available, without further sample contracts (the agent's decision):
the Iowa REALTORS® form ¶9 ([review](PURCHASE-AGREEMENT-REVIEW.md)), closed transaction #1, an attorney closing
([validation](VALIDATION-CLOSED-TRANSACTION-1.md)), and the 360-day-year convention common in licensing courses.
Code: `netsheet/calculations/property_tax.py`.

1. **Fiscal year of possession:** the July 1 – June 30 year containing the **possession date**. If no possession date
   is entered, the closing date is used (form ¶4: possession at closing).
2. **Bill due after possession** (¶9, "taxes due and payable in the fiscal year in which possession is given"): the
   bill due in September and March of that fiscal year. Each installment the seller hasn't paid is charged to the seller.
   If that bill isn't entered yet (counties usually issue it in August), it is **estimated from the prior-year bill**.
   If an installment's paid status is "Not sure," it is charged and flagged.
3. **Proration** (¶9, prorated "as of the date of possession," based on "the taxes that were certified and payable
   in the prior fiscal year"): prior-year bill × seller days ÷ 360.
   - **360 setting (default):** 30 days for each full month since July 1, plus the day of the month, up to 30.
   - **365 setting:** actual calendar days ÷ 365.
   - **Possession day:** counted as the seller's by default. Can be switched to buyer.
4. **¶9 special case** (taxes not based on a full assessment of current improvements, e.g. new construction):
   **not calculated.** The agent enters the amount manually.
5. You can always choose **"I'll enter the amounts myself"** instead, and add extra tax lines, such as delinquent
   taxes, either way.

Everything is labeled **ESTIMATED** except installments taken from an entered county bill. Closing agents
(attorneys, Escrow Plus, lenders) may calculate slightly differently, for example by actual days.

**Check against closed transaction #1:** the app gives $2,488.00 + $2,488.00 + $414.67 = **$5,390.67**. The settlement
statement shows **$5,390.68**, a 1-cent difference from county bills being rounded to whole dollars.

## Audit trail

Every transaction fact records where it came from: *Entered by agent*, or, in the future, *Purchase
Agreement page X, with the exact wording*, which needs your confirmation before it's trusted.
Every save is recorded in `audit-log.jsonl` with the old and new values.
