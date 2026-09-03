"""
Core reconciliation logic, in plain Python.

This is the heart of the project and the thing you can whiteboard in the interview:
given two lists of payments keyed by transaction_id, classify every transaction as
MATCHED / MISSING_IN_PROCESSOR / UNEXPECTED_IN_PROCESSOR / AMOUNT_MISMATCH.

We keep this pure (no database, no I/O) so it is trivial to unit-test. That is the
TDD-friendly design: the logic is a function of its inputs.
"""

from dataclasses import dataclass
from typing import Iterable


# a cent-level tolerance so floating point noise doesn't create false mismatches
AMOUNT_TOLERANCE = 0.005


@dataclass(frozen=True)
class ReconResult:
    transaction_id: str
    status: str
    internal_amount: float | None
    processor_amount: float | None

    @property
    def amount_difference(self) -> float | None:
        if self.internal_amount is None or self.processor_amount is None:
            return None
        return round(self.internal_amount - self.processor_amount, 2)


def reconcile(
    internal: Iterable[dict],
    processor: Iterable[dict],
) -> list[ReconResult]:
    """Compare two payment sources and classify every transaction.

    internal rows:  {"transaction_id": str, "amount": float, ...}
    processor rows: {"transaction_id": str, "settled_amount": float, ...}
    """
    internal_by_id = {r["transaction_id"]: float(r["amount"]) for r in internal}
    processor_by_id = {
        r["transaction_id"]: float(r["settled_amount"]) for r in processor
    }

    all_ids = sorted(set(internal_by_id) | set(processor_by_id))
    results: list[ReconResult] = []

    for txn_id in all_ids:
        in_amt = internal_by_id.get(txn_id)
        pr_amt = processor_by_id.get(txn_id)

        if in_amt is not None and pr_amt is None:
            status = "MISSING_IN_PROCESSOR"
        elif in_amt is None and pr_amt is not None:
            status = "UNEXPECTED_IN_PROCESSOR"
        elif abs(in_amt - pr_amt) <= AMOUNT_TOLERANCE:
            status = "MATCHED"
        else:
            status = "AMOUNT_MISMATCH"

        results.append(ReconResult(txn_id, status, in_amt, pr_amt))

    return results


def summarize(results: list[ReconResult]) -> dict[str, int]:
    """Count results by status, for a quick report / dashboard feed."""
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    return counts
