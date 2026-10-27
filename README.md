# Iowa Seller Net Sheet — Phase 1

A simple, private seller net sheet app that runs on your Mac and opens in your web browser.
Nothing is sent over the internet. Nothing is sent to clients. Your files stay on your Mac.

## What it does now

- **Two ways to start:** *Listing appointment* (no contract, hypothetical price) or *Under contract*.
- **Purchase Agreement:** upload the PDF. The app stores a **read-only copy** and a digital
  fingerprint of it. Your original file is never moved or changed. You can view the contract beside the form while you type.
- **Every cost line can be marked Estimated or Actual.** Estimated items show **EST.** on screen and on the PDF.
- **Real estate compensation:** separate lines for listing brokerage, seller-paid buyer brokerage,
  and brokerage/admin fees. No rate is assumed. Choose percentage, flat amount, or both.
- **Payoffs:** as many as you need. Good-through date and daily interest are optional.
- **Iowa transfer tax:** calculated automatically, with every step of the math shown (Iowa Code §428A.1).
- **Property taxes:** calculated from your Purchase Agreement's ¶9 and the county tax bills, with all the math
  shown and labeled ESTIMATED. Settings for 360 or 365 days and who is charged for the possession day. Or enter the
  amounts yourself.
- **Abstract continuation and deed preparation:** each has its own line, with an optional provider name.
- **Optional costs and credits:** click a suggestion (septic inspection, home warranty, repairs, etc.)
  or add your own. Nothing appears unless you add it.
- **Agent View** (math, sources, warnings) and **Client View** (clean, with the estimate disclaimer).
- **PDFs:** each one is saved as a new numbered version (v001, v002 …). Earlier versions are never replaced.
- **History:** a permanent log of every change, upload, and PDF.
- **Compare to Settlement:** type in the final settlement figures from a closed deal to see every difference.

## Where things are kept

`Documents/Seller Net Sheets/` gets one folder per property:

| File | What it is |
|---|---|
| `net-sheet-data.json` | Current figures, plus where each one came from |
| `audit-log.jsonl` | Permanent history of changes |
| `Purchase Agreement (copy).pdf` | Read-only copy of the contract you uploaded |
| `Generated Net Sheets/` | Every PDF version, each with a matching data snapshot |

## How to install and start it

See **[docs/INSTALL-ON-MAC.md](docs/INSTALL-ON-MAC.md)**.

## How the numbers are calculated

See **[docs/CALCULATIONS-AND-SOURCES.md](docs/CALCULATIONS-AND-SOURCES.md)**.

## Not built yet (future phases)

- AI-assisted contract reading. The slot for it is built, and suggestions will always need your approval.
- Brokerage branding on the client PDF.
- Google Drive, county tax lookups, email. **The app does not access any of these.**

## For a technical helper

Python 3.11+, Flask, ReportLab. Run the self-checks with `uv run pytest`. Start with `uv run python -m netsheet`.
All money math uses `Decimal`. The calculation code is in `netsheet/calculations/` and has no web or file-system
dependencies. Property-tax proration (`property_tax.py`) follows the Iowa REALTORS® form ¶9; see docs/CALCULATIONS-AND-SOURCES.md.
