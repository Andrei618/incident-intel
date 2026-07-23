"""Metrics for measuring retrieval quality."""

from collections.abc import Sequence


def recall_at_k(retrieved: Sequence, relevant: set, k: int) -> float | None:
    """Compute fraction of relevant items that appear in the top-k.

    Args:
        retrieved: an ordered, best-first sequence of chunk IDs.
        relevant: the ground-truth set.
        k: the cutoff. k is assumed >= 1.

    Returns:
        recall in [0, 1], and None when relevant is empty.
    """
    if not relevant:
        return None
    top_k = retrieved[:k]
    hits = set(top_k) & relevant
    return len(hits) / len(relevant)


def precision_at_k(retrieved: Sequence, relevant: set, k: int) -> float | None:
    """Compute fraction of top-k items that are relevant.

    Args:
        retrieved: an ordered, best-first sequence of chunk IDs.
        relevant: the ground-truth set.
        k: the cutoff. k is assumed >= 1.

    Returns:
        precision in [0, 1], and None when relevant is empty.
    """
    if not relevant:
        return None
    top_k = retrieved[:k]
    hits = set(top_k) & relevant
    return len(hits) / k


def reciprocal_rank_at_k(retrieved: Sequence, relevant: set, k: int) -> float | None:
    """Compute reciprocal rank based on position of the first relevant item.

    The mean (MRR) is applied at aggregation.

    Args:
        retrieved: an ordered, best-first sequence of chunk IDs.
        relevant: the ground-truth set.
        k: the cutoff. k is assumed >= 1.

    Returns:
        reciprocal rank in [0, 1], None when relevant is empty and 0.0 when no relevant item is in the top-k.
    """
    if not relevant:
        return None
    top_k = retrieved[:k]
    for i, item in enumerate(top_k, start=1):
        if item in relevant:
            return 1 / i
    return 0.0
