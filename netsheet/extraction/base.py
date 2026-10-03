"""Contract-reading plug-in point.

Phase 1 ships only the ManualProvider, which suggests nothing: the agent types
every value while viewing the contract side by side.

A future AI provider (e.g. Claude) must implement the same interface and return
Suggestions that carry the exact contract wording and page number. Suggestions
are NEVER used directly — apply_suggestions() stores them as unconfirmed, and
the net sheet shows "NEEDS REVIEW" until the agent confirms each one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .. import models


@dataclass
class Suggestion:
    fact_key: str  # one of models.FACTS
    value: str
    page: int | None
    quote: str  # exact wording from the contract
    uncertain: bool = False
    note: str = ""


@dataclass
class ReviewFlag:
    text: str  # why the agent should look at this provision
    page: int | None
    quote: str


@dataclass
class ExtractionResult:
    suggestions: list[Suggestion] = field(default_factory=list)
    review_flags: list[ReviewFlag] = field(default_factory=list)
    provider: str = ""


class ExtractionProvider(Protocol):
    name: str

    def extract(self, pdf_bytes: bytes) -> ExtractionResult: ...


class ManualProvider:
    name = "manual"

    def extract(self, pdf_bytes: bytes) -> ExtractionResult:
        return ExtractionResult(provider=self.name)


def apply_suggestions(tx: dict, result: ExtractionResult) -> None:
    """Store suggestions as UNCONFIRMED. Never overwrites a value the agent
    has already entered — those are kept and the suggestion is turned into a
    review item instead."""
    for s in result.suggestions:
        if s.fact_key not in models.FACTS:
            continue
        current = tx["facts"][s.fact_key]
        if current.get("value") and current.get("source") == "manual":
            tx["review_items"].append({
                "id": models.new_id(),
                "text": f"Contract suggests {models.FACTS[s.fact_key][0]} = '{s.value}', "
                        f"but you entered '{current['value']}'. Decide which is correct.",
                "page": s.page, "quote": s.quote, "source": result.provider,
                "resolved": False, "resolution": "",
            })
            continue
        tx["facts"][s.fact_key] = {
            "value": s.value, "source": "contract", "page": s.page, "quote": s.quote,
            "confirmed": False, "uncertain": s.uncertain, "note": s.note,
            "provider": result.provider, "updated_at": models.now_iso(),
        }
    for f in result.review_flags:
        tx["review_items"].append({
            "id": models.new_id(), "text": f.text, "page": f.page, "quote": f.quote,
            "source": result.provider, "resolved": False, "resolution": "",
        })
