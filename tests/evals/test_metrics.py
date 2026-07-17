"""Unit tests for evaluation metrics."""

from tests.evals.metrics import precision_at_k, recall_at_k, reciprocal_rank_at_k


def test_recall_at_k_returns_none_when_empty_relevant() -> None:
    """Test recall_at_k returns None when relevant set is empty."""
    # Arrange
    retrieved = ["A"]
    relevant = set()
    k = 3

    # Act
    result = recall_at_k(retrieved, relevant, k)

    # Assert
    assert result is None


def test_recall_at_k_k_slice_actually_cuts() -> None:
    """Test recall_at_k returns 0.0 when relevant is outside of top-k: A sits at position 5, outside top-3."""
    # Arrange
    retrieved = ["X", "X", "X", "X", "A"]
    relevant = {"A"}
    k = 3

    # Act
    result = recall_at_k(retrieved, relevant, k)

    # Assert
    assert result == 0.0


def test_recall_at_k_returns_between_0_and_1_for_partial_covering() -> None:
    """Test recall_at_k returns number between 0.0 and 1.0 if retrieved partially covers relevant set."""
    # Arrange
    retrieved = ["X", "A"]
    relevant = {"A", "B"}
    k = 2

    # Act
    result = recall_at_k(retrieved, relevant, k)

    # Assert
    assert result == 0.5


def test_precision_at_k_returns_between_0_and_1_when_k_larger_than_relevant_set_length() -> None:
    """Test precision_at_k returns number between 0.0 and 1.0 when k larger than length of relevant set."""
    # Arrange
    retrieved = ["A", "X", "Y", "Z", "W"]
    relevant = {"A"}
    k = 5

    # Act
    result = precision_at_k(retrieved, relevant, k)

    # Assert
    assert result == 0.2


def test_precision_at_k_returns_none_for_empty_relevant() -> None:
    """Test precision_at_k returns None if relevant set is empty."""
    # Arrange
    retrieved = ["A"]
    relevant = set()
    k = 5

    # Act
    result = precision_at_k(retrieved, relevant, k)

    # Assert
    assert result is None


def test_reciprocal_rank_at_k_returns_1_when_relevant_in_first_slot() -> None:
    """Test reciprocal_rank_at_k returns 1.0 when relevant is on the first position in retrieved."""
    # Arrange
    retrieved = ["A", "B", "X"]
    relevant = {"A", "B"}
    k = 2

    # Act
    result = reciprocal_rank_at_k(retrieved, relevant, k)

    # Assert
    assert result == 1.0


def test_reciprocal_rank_at_k_returns_between_0_and_1_when_relevant_is_not_first_slot() -> None:
    """Test reciprocal_rank_at_k returns number between 0.0 and 1.0 when relevant is not on the first position in retrieved."""
    # Arrange
    retrieved = ["X", "A", "B"]
    relevant = {"A", "B"}
    k = 2

    # Act
    result = reciprocal_rank_at_k(retrieved, relevant, k)

    # Assert
    assert result == 0.5


def test_reciprocal_rank_at_k_returns_0_when_relevant_not_in_top_k() -> None:
    """Test reciprocal_rank_at_k returns 0.0 when relevant is not in top-k."""
    # Arrange
    retrieved = ["X", "Y", "A", "B"]
    relevant = {"A", "B"}
    k = 2

    # Act
    result = reciprocal_rank_at_k(retrieved, relevant, k)

    # Assert
    assert result == 0.0
