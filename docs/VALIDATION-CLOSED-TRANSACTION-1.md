# Validation — closed transaction #1

**Property:** Cerro Gordo County, Iowa (names, address and file number left out of this repository).
**Source:** final HUD-1 settlement statement prepared by the settlement agent, settlement date **July 31, 2026**.
**Not yet received:** the executed Purchase Agreement (both scans uploaded so far were blank), and the
county tax amounts for this parcel.

## Line-by-line comparison (seller side)

| Item | Settlement statement | App | Match? |
|---|---|---|---|
| Sale price | $610,000.00 (line 401) | $610,000.00 | ✅ |
| Commission, 5% of price | $30,500.00 (line 700) = $29,500.00 paid at settlement (703) + $1,000.00 deposit retained by broker (506) | $610,000 × 5% = $30,500.00 | ✅ (see note 1) |
| Iowa transfer tax (revenue stamps) | $975.20 (line 1202) | **calculated** (610,000 − 500) ÷ 500 = 1,219 × $0.80 = **$975.20** | ✅ independent match |
| Abstract continuation | $430.00 (1102, Cerro Gordo Abstract Company) | entered | ✅ |
| Deed / document preparation | $360.00 (1105, Laird Law Firm) | entered | ✅ |
| Courier fee | $40.00 (1104) | entered as other cost | ✅ |
| File affidavits (recording) | $7.00 (1205) | entered as other cost | ✅ (see note 2) |
| Mortgage payoff | $212,716.06 (504) | entered | ✅ |
| County taxes **07/01/25 to 07/31/26** | $5,390.68 (511) | entered manually | ⏳ method not yet verified |
| **Cash to seller** | **$359,581.06 (603)** | **$359,581.06** | ✅ to the penny |

The settlement agent charged the seller nothing for the settlement fee, title examination, recording, or pest
inspection on this file. The buyer paid those.

## Notes

1. **Earnest money held by the broker.** The $1,000 earnest money was kept by the broker and counted toward the
   commission. The app's approach is confirmed: the full commission is a seller cost and earnest money is not
   subtracted again. The app now explains this on screen.
2. **"File affidavits" ($7).** This is a small recording charge the app had no suggestion for. The sellers were trusts,
   so it may be a trustee affidavit. It is entered as a custom line.

## Property taxes: what this file shows

The tax line is a **single debit to the seller covering July 1, 2025 through July 31, 2026** (396 days). That fits
form ¶9 with possession on July 31, 2026:
- **Part A:** the seller pays the taxes due and payable in fiscal year 2026-27. Those are the September 2026
  and March 2027 installments, which cover July 1, 2025 – June 30, 2026. Neither was paid at closing.
- **Part B:** the seller pays July 1 – July 31, 2026 of the 2026-27 fiscal year, prorated.

**$5,390.68 can be produced by more than one method,** so the method can't be confirmed yet:

| Possible method | Annual tax needed to get $5,390.68 |
|---|---|
| One annual amount × 396 ÷ 365 days | $4,968.68 |
| One annual amount × 13 months ÷ 12 | $4,976.01 |
| Two different annual amounts (Part A uses one bill, Part B uses the other) | depends on both county bills |

### Update 2026-10-27: county tax history received

Source: county treasurer's parcel tax history (screenshot from the agent, viewed 2026-10-27).

| Tax year | Payable | Installments | Annual |
|---|---|---|---|
| 2024 | Sept 2025 / Mar 2026 (fiscal year 2025-26) | $2,488 + $2,488, both paid by the seller before closing | **$4,976** |
| 2025 | Sept 2026 / Mar 2027 (fiscal year 2026-27) | $2,432 + $2,432; first paid 9/28/2026 (after closing), second still due | **$4,864** |

Every combination tested against the settlement figure of $5,390.68:

| Method | Result | Difference |
|---|---|---|
| **$4,976 × 13 months ÷ 12** (2024 bill for all 13 months) | **$5,390.67** | **−$0.01** |
| $4,976 + $4,864 × 31 ÷ 365 | $5,389.11 | −$1.57 |
| $4,976 × 396 ÷ 365 (daily) | $5,398.62 | +$7.94 |
| $4,976 + $4,864 ÷ 12 | $5,381.33 | −$9.35 |
| $4,864 + July at either rate (2025 bill for the full year) | $5,277–$5,287 | about −$104 to −$114 |
| $4,864 × 13 months ÷ 12 | $5,269.33 | −$121.35 |

**Finding:** the closing attorney charged the seller **13 months (July 2025 – July 2026) at the 2024 tax bill
($4,976 a year), counted in whole months.** That bill is the one "certified and payable in the prior fiscal year,"
so this matches **Reading A** of ¶9. The 1-cent gap is most likely because county bills are rounded to whole dollars:
an unrounded annual tax of about $4,976.01 gives exactly $5,390.68. A 1982 Iowa act required tax bills to be
rounded to the nearest even dollar; whether that is still current law was not verified.

**Observation (not an interpretation):** the 2025 bill that actually came due after closing was $4,864, which is
$112 a year lower. It was probably not issued yet on July 31, 2026, because Iowa tax statements usually come out in
August. The settlement statement shows no later adjustment.

**What this transaction can't show,** because possession fell on the last day of a month and in July:
1. How a **partial month** is counted (for example, possession on the 15th): by days, or by a 30-day month?
2. Possession **after September**, when the seller has already paid the first installment of the new bill.
3. Possession **March–June**, when both installments are already paid.
4. Whether the attorney switches to the **new bill once it is issued** (August onward).

**Next:** one or two more closed transactions with mid-month possession, ideally one between October and February
and one between March and June.
