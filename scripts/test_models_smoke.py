"""Smoke tests for database models.

Verifies model definitions without database connection.
Run after creating/modifying models to catch syntax errors.
"""

from incident_intel.models.base import Base
from incident_intel.models.service import Service
from incident_intel.models.tickets import (
    Ticket,
    TicketStatus,
    TicketPriority,
    TicketComment,
)


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

def test_ticket_model() -> None:
    """Verify Ticket model is defined correctly."""
    print("Testing Ticket model ...")

    # Test 1: Table name
    assert Ticket.__tablename__ == "tickets", (
        f"Expected 'tickets'. got '{Ticket.__tablename__}'"
    )
    print("  ✅ Table name: tickets")

    # Test 2: Columns exist
    columns = {c.name for c in Ticket.__table__.columns}
    expected = {
        "id",
        "service_id",
        "title",
        "description",
        "status",
        "priority",
        "created_at",
        "updated_at",
        "resolved_at",
        "assignee",
        "reporter",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"
    print(f"  ✅ All {len(columns)} columns defined")

    # Test 3: Can create instance
    ticket = Ticket(
        title="API Error",
        status=TicketStatus.OPEN,
        priority=TicketPriority.P1,
    )
    assert ticket.title == "API Error"
    assert ticket.status is TicketStatus.OPEN
    assert ticket.priority is TicketPriority.P1
    print("  ✅ Can create instance")

    # Test 4: Inherits from Base and TimestampMixin
    assert isinstance(ticket, Base)
    assert hasattr(ticket, "created_at")
    assert hasattr(ticket, "updated_at")
    print("  ✅ Inherits from Base and TimestampMixin")

    # Test 5: Nullable Defaults Are None
    assert ticket.resolved_at is None, "Open tickets must have resolved_at=None"
    print("  ✅ resolved_at defaults to None")

    # Test 6: Check indexes exist
    indexes = {ix.name for ix in ticket.__table__.indexes}
    expected_indexes = {"ix_tickets_status", "ix_tickets_priority", "ix_tickets_created"}
    assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"
    print("  ✅ Indexes exist")

    # Test 7: Relationships exist
    assert hasattr(Ticket, "service")
    print("  ✅ Relationships defined")

    # Test 8: Check constraints
    constraints = {c.name for c in ticket.__table__.constraints}
    assert "ck_tickets_resolved_requires_status" in constraints, "Missing CHECK constraints"
    print("  ✅ CHECK constraint 'ck_tickets_resolved_requires_status' defined")

    print("✅ Ticket model: ALL TESTS PASSED\n")


def test_ticket_comment_model() -> None:
    """Verify TicketComment model is defined correctly."""
    print("Testing TicketComment model ...")

    # Test 1: Table name
    assert TicketComment.__tablename__ == "ticket_comments", (
        f"Expected 'ticket_comments'. got '{TicketComment.__tablename__}'"
    )
    print("  ✅ Table name: ticket_comments")

    # Test 2: Columns exist
    columns = {c.name for c in TicketComment.__table__.columns}
    expected = {
        "id",
        "ticket_id",
        "author",
        "content",
        "created_at",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"
    print(f"  ✅ All {len(columns)} columns defined")

    # Test 3: Can create instance
    ticket_comment = TicketComment(
        author="Test Name",
        content="Ticket is closed",
    )
    assert ticket_comment.author == "Test Name"
    assert ticket_comment.content == "Ticket is closed"
    print("  ✅ Can create instance")

    # Test 4: Inherits from Base
    assert isinstance(ticket_comment, Base)
    print("  ✅ Inherits from Base")

    # Test 5: Check indexes exist
    indexes = {ix.name for ix in ticket_comment.__table__.indexes}
    expected_indexes = {"ix_ticket_comments_ticket"}
    assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"
    print("  ✅ Indexes exist")

    # Test 6: Relationships exist
    assert hasattr(TicketComment, "ticket")
    print("  ✅ Relationships defined")

    print("✅ TicketComment model: ALL TESTS PASSED\n")

if __name__ == "__main__":
    print("=" * 50)
    print("DATABASE MODELS SMOKE TESTS")
    print("=" * 50 + "\n")

    test_service_model()
    test_ticket_model()
    test_ticket_comment_model()
    # test_document_model()

    print("=" * 50)
    print("ALL SMOKE TESTS PASSED ✅")
    print("=" * 50)
