"""Iowa property-tax proration — PENDING. NOT IMPLEMENTED ON PURPOSE.

The proration method in Iowa is controlled by the wording of the Purchase
Agreement, not by a single statutory formula. Per the agent's instruction
(2026-10-03), no proration rule may be encoded until:
  1. the agent's actual Purchase Agreement form has been reviewed, and
  2. the method has been validated against a real closed transaction's
     final settlement statement, and
  3. the agent has approved the method in writing.

Until then, the app only accepts property-tax amounts that the agent types in
(from the title company, the closing attorney, or the agent's own figures). Those
amounts are labeled "entered manually — not calculated by this app".
"""

from __future__ import annotations

STATUS = "pending"

PENDING_MESSAGE = (
    "Property-tax proration is NOT calculated by this app yet. The method is pending "
    "review of your Purchase Agreement form and validation against a closed transaction. "
    "Any property-tax amounts shown were entered manually."
)


class ProrationMethodNotApproved(NotImplementedError):
    pass


def calculate_proration(*args, **kwargs):
    raise ProrationMethodNotApproved(PENDING_MESSAGE)
