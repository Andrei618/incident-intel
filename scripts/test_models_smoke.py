"""Smoke tests for database models.

Verifies model definitions without database connection.
Run after creating/modifying models to catch syntax errors.
"""

from incident_intel.models.base import Base
from incident_intel.models.service import Service


def test_service_model() -> None:
    """Verify Service model is defined correctly."""
    print("Testing Service model...")

    # Test 1: Table name
    assert Service.__tablename__ == "services", (
        f"Expected 'services'. got '{Service.__tablename__}'"
    )
    print("  ✅ Table name: services")

    # Test 2: Columns exist
    columns = {c.name for c in Service.__table__.columns}
    expected = {
        "id",
        "name",
        "description",
        "sla_p1_minutes",
        "sla_p2_minutes",
        "sla_p3_minutes",
        "sla_p4_minutes",
        "created_at",
        "updated_at",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"
    print(f"  ✅ All {len(columns)} columns defined")

    # Test 3: Can create instance
    service = Service(
        name="Payment Service",
        description="Handles payment processing",
    )
    assert service.name == "Payment Service"
    print("  ✅ Can create instance")

    # Test 4: Check column defaults (in table metadata, not instance)
    sla_p1_col = Service.__table__.columns["sla_p1_minutes"]
    assert sla_p1_col.default.arg == 60, "Wrong default for sla_p1_minutes"
    print("  ✅ Column defaults are correct")

    # Test 5: Inherits from Base and TimestampMixin
    assert isinstance(service, Base)
    assert hasattr(service, "created_at")
    assert hasattr(service, "updated_at")
    print("  ✅ Inherits from Base and TimestampMixin")

    print("✅ Service model: ALL TESTS PASSED\n")


if __name__ == "__main__":
    print("=" * 50)
    print("DATABASE MODELS SMOKE TESTS")
    print("=" * 50 + "\n")

    test_service_model()
    # Add more model tests here as you create them
    # test_ticket_model()
    # test_document_model()

    print("=" * 50)
    print("ALL SMOKE TESTS PASSED ✅")
    print("=" * 50)
