"""
Unit tests for the reconciliation logic.

These are written the TDD way: each test states an expected behavior first, and the
reconcile() function has to satisfy it. Because reconcile() is pure (inputs -> outputs
with no database), the tests are fast and deterministic.

Run:  pytest -v
"""

import sys
from pathlib import Path

# make scripts/ importable without installing a package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from reconcile import reconcile, summarize, ReconResult  # noqa: E402


def _internal(txn_id, amount):
    return {"transaction_id": txn_id, "amount": amount}


def _processor(txn_id, amount):
    return {"transaction_id": txn_id, "settled_amount": amount}


def test_perfect_match_is_matched():
    results = reconcile([_internal("TXN1", 100.00)], [_processor("TXN1", 100.00)])
    assert len(results) == 1
    assert results[0].status == "MATCHED"


def test_in_internal_only_is_missing_in_processor():
    results = reconcile([_internal("TXN1", 100.00)], [])
    assert results[0].status == "MISSING_IN_PROCESSOR"
    assert results[0].processor_amount is None


def test_in_processor_only_is_unexpected():
    results = reconcile([], [_processor("TXN1", 100.00)])
    assert results[0].status == "UNEXPECTED_IN_PROCESSOR"
    assert results[0].internal_amount is None


def test_different_amounts_is_amount_mismatch():
    results = reconcile([_internal("TXN1", 100.00)], [_processor("TXN1", 95.00)])
    assert results[0].status == "AMOUNT_MISMATCH"
    assert results[0].amount_difference == 5.00


def test_tiny_floating_point_difference_still_matches():
    # 100.001 vs 100.00 should NOT be flagged; within tolerance
    results = reconcile([_internal("TXN1", 100.001)], [_processor("TXN1", 100.00)])
    assert results[0].status == "MATCHED"


def test_summary_counts_each_status():
    internal = [_internal("A", 10), _internal("B", 20), _internal("C", 30)]
    processor = [_processor("A", 10), _processor("B", 999), _processor("D", 40)]
    results = reconcile(internal, processor)
    counts = summarize(results)
    assert counts["MATCHED"] == 1            # A
    assert counts["AMOUNT_MISMATCH"] == 1    # B
    assert counts["MISSING_IN_PROCESSOR"] == 1  # C
    assert counts["UNEXPECTED_IN_PROCESSOR"] == 1  # D


def test_results_are_sorted_by_transaction_id():
    results = reconcile(
        [_internal("TXN3", 1), _internal("TXN1", 1)],
        [_processor("TXN2", 1)],
    )
    ids = [r.transaction_id for r in results]
    assert ids == sorted(ids)
