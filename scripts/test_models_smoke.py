"""Smoke tests for database models.

Verifies model definitions without database connection.
Run after creating/modifying models to catch syntax errors.
"""

from sqlalchemy import UniqueConstraint

from incident_intel.models.base import Base
from incident_intel.models.conversation import Conversation, Message, MessageRole
from incident_intel.models.document import DocType, Document, DocumentChunk
from incident_intel.models.review import PendingReview, ReviewStatus
from incident_intel.models.service import Service
from incident_intel.models.ticket_documents import TicketDocument
from incident_intel.models.tickets import (
    Ticket,
    TicketComment,
    TicketPriority,
    TicketStatus,
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
    assert Ticket.__tablename__ == "tickets", f"Expected 'tickets'. got '{Ticket.__tablename__}'"
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


def test_document_model() -> None:
    """Verify Document model is defined correctly."""
    print("Testing Document model ...")

    # Test 1: Table name
    assert Document.__tablename__ == "documents", (
        f"Expected 'documents'. got '{Document.__tablename__}'"
    )
    print("  ✅ Table name: documents")

    # Test 2: Columns exist
    columns = {c.name for c in Document.__table__.columns}
    expected = {
        "id",
        "service_id",
        "title",
        "content",
        "doc_type",
        "created_at",
        "updated_at",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"
    print(f"  ✅ All {len(columns)} columns defined")

    # Test 3: Can create instance
    document = Document(
        title="Test Title",
        content="Test document content",
        doc_type=DocType.RUNBOOK,
    )
    assert document.title == "Test Title"
    assert document.content == "Test document content"
    assert document.doc_type == DocType.RUNBOOK
    print("  ✅ Can create instance")

    # Test 4: Inherits from Base and TimestampMixin
    assert isinstance(document, Base)
    assert hasattr(document, "created_at")
    assert hasattr(document, "updated_at")
    print("  ✅ Inherits from Base and TimestampMixin")

    # Test 5: Check indexes exist
    indexes = {ix.name for ix in document.__table__.indexes}
    expected_indexes = {"ix_documents_service_id"}
    assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"
    print("  ✅ Indexes exist")

    # Test 6: Relationships exist
    assert hasattr(Document, "document_chunks")
    assert hasattr(Document, "service")
    print("  ✅ Relationships defined")

    # Test 7: Check constraints
    constraints = {c.name for c in document.__table__.constraints}
    assert "ck_documents_valid_doc_type" in constraints, "Missing CHECK constraints"
    print("  ✅ CHECK constraint 'ck_documents_valid_doc_type' defined")

    print("✅ Document model: ALL TESTS PASSED\n")


def test_document_chunk_model() -> None:
    """Verify DocumentChunk model is defined correctly."""
    print("Testing DocumentChunk model ...")

    # Test 1: Table name
    assert DocumentChunk.__tablename__ == "document_chunks", (
        f"Expected 'documents'. got '{DocumentChunk.__tablename__}'"
    )
    print("  ✅ Table name: document_chunks")

    # Test 2: Columns exist
    columns = {c.name for c in DocumentChunk.__table__.columns}
    expected = {
        "id",
        "document_id",
        "content",
        "embedding",
        "chunk_index",
        "metadata",  # Database column name (Python attribute is chunk_metadata)
    }
    assert columns == expected, f"Missing columns: {expected - columns}"
    print(f"  ✅ All {len(columns)} columns defined")

    # Test 3: Can create instance
    document_chunk = DocumentChunk(
        content="Test document chunk content",
        chunk_index=123,
        chunk_metadata={"test_key": "test_value"},
    )
    assert document_chunk.content == "Test document chunk content"
    assert document_chunk.chunk_index == 123
    assert document_chunk.chunk_metadata == {"test_key": "test_value"}
    print("  ✅ Can create instance")

    # Test 4: Inherits from Base
    assert isinstance(document_chunk, Base)
    print("  ✅ Inherits from Base")

    # Test 5: Check indexes exist
    indexes = {ix.name for ix in document_chunk.__table__.indexes}
    expected_indexes = {"ix_document_chunks_embedding"}  # content_tsv index created via migration
    assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"
    print("  ✅ Indexes exist")

    # Test 6: Relationships exist
    assert hasattr(DocumentChunk, "document")
    print("  ✅ Relationships defined")

    print("✅ DocumentChunk model: ALL TESTS PASSED\n")

def test_ticket_documents_model() -> None:
    """Verify TicketDocument model is defined correctly."""
    print("Testing TicketDocument model ...")

    # Test 1: Table name
    assert TicketDocument.__tablename__ == "ticket_documents", (
        f"Expected 'documents'. got '{TicketDocument.__tablename__}'"
    )
    print("  ✅ Table name: ticket_documents")

    # Test 2: Columns exist
    columns = {c.name for c in TicketDocument.__table__.columns}
    expected = {
        "id",
        "ticket_id",
        "document_id",
        "relevance_score",
        "linked_at",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"
    print(f"  ✅ All {len(columns)} columns defined")

    # Test 3: Can create instance
    ticket_document = TicketDocument()
    assert isinstance(ticket_document, TicketDocument)
    print("  ✅ Can create instance")

    # Test 4: Inherits from Base
    assert isinstance(ticket_document, Base)
    print("  ✅ Inherits from Base")

    # Test 5: Check indexes exist
    indexes = {ix.name for ix in ticket_document.__table__.indexes}
    expected_indexes = {"ix_ticket_documents_ticket_id", "ix_ticket_documents_document_id"}
    assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"
    print("  ✅ Indexes exist")

    # Test 6: Relationships exist
    assert hasattr(TicketDocument, "ticket")
    assert hasattr(TicketDocument, "document")
    print("  ✅ Relationships defined")

    # Test 7: Check constraints
    constraints = {c.name for c in ticket_document.__table__.constraints
                    if isinstance(c, UniqueConstraint)}
    assert len(constraints), "Missing UNIQUE constraint"
    print("  ✅ UNIQUE constraint defined")

    print("✅ TicketDocument model: ALL TESTS PASSED\n")


def test_conversation_model() -> None:
    """Verify Conversation model is defined correctly."""
    print("Testing Conversation model ...")

    # Test 1: Table name
    assert Conversation.__tablename__ == "conversations", (
        f"Expected 'conversations'. got '{Conversation.__tablename__}'"
    )
    print("  ✅ Table name: conversations")

    # Test 2: Columns exist
    columns = {c.name for c in Conversation.__table__.columns}
    expected = {
        "id",
        "user_id",
        "created_at",
        "updated_at",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"
    print(f"  ✅ All {len(columns)} columns defined")

    # Test 3: Can create instance
    conversation = Conversation()
    assert isinstance(conversation, Conversation)
    print("  ✅ Can create instance")

    # Test 4: Inherits from Base and TimestampMixin
    assert isinstance(conversation, Base)
    assert hasattr(conversation, "created_at")
    assert hasattr(conversation, "updated_at")
    print("  ✅ Inherits from Base and TimestampMixin")

    # Test 5: Check indexes exist
    indexes = {ix.name for ix in conversation.__table__.indexes}
    expected_indexes = {"ix_conversations_user_id"}
    assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"
    print("  ✅ Indexes exist")

    # Test 6: Relationships exist
    assert hasattr(Conversation, "messages")
    print("  ✅ Relationships defined")

    print("✅ Conversation model: ALL TESTS PASSED\n")


def test_message_model() -> None:
    """Verify Message model is defined correctly."""
    print("Testing Message model ...")

    # Test 1: Table name
    assert Message.__tablename__ == "messages", (
        f"Expected 'messages'. got '{Message.__tablename__}'"
    )
    print("  ✅ Table name: messages")

    # Test 2: Columns exist
    columns = {c.name for c in Message.__table__.columns}
    expected = {
        "id",
        "conversation_id",
        "role",
        "content",
        "token_count",
        "created_at",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"
    print(f"  ✅ All {len(columns)} columns defined")

    # Test 3: Can create instance
    message = Message(
        role=MessageRole.USER,
        content="Test message content",
    )
    assert message.role == MessageRole.USER
    assert message.content == "Test message content"
    print("  ✅ Can create instance")

    # Test 4: Inherits from Base
    assert isinstance(message, Base)
    print("  ✅ Inherits from Base")

    # Test 5: Check indexes exist
    indexes = {ix.name for ix in message.__table__.indexes}
    expected_indexes = {"ix_messages_conversation"}
    assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"
    print("  ✅ Indexes exist")

    # Test 6: Relationships exist
    assert hasattr(Message, "conversation")
    print("  ✅ Relationships defined")


    # Test 7: Check constraints
    constraints = {c.name for c in message.__table__.constraints}
    assert "ck_messages_valid_role" in constraints, "Missing CHECK constraints"
    print("  ✅ CHECK constraint 'ck_messages_valid_role' defined")

    print("✅ Message model: ALL TESTS PASSED\n")

def test_pending_review_model() -> None:
    """Verify PendingReview model is defined correctly."""
    print("Testing PendingReview model ...")

    # Test 1: Table name
    assert PendingReview.__tablename__ == "pending_reviews", (
        f"Expected 'pending_reviews'. got '{PendingReview.__tablename__}'"
    )
    print("  ✅ Table name: pending_reviews")

    # Test 2: Columns exist
    columns = {c.name for c in PendingReview.__table__.columns}
    expected = {
        "id",
        "conversation_id",
        "question",
        "generated_answer",
        "confidence_score",
        "sources",
        "status",
        "reviewer_notes",
        "created_at",
        "reviewed_at",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"
    print(f"  ✅ All {len(columns)} columns defined")

    # Test 3: Can create instance
    pending_review = PendingReview(
        question="Test question",
        generated_answer="Test answer",
        confidence_score=0.75,
        status=ReviewStatus.PENDING,
    )
    assert pending_review.question == "Test question"
    assert pending_review.generated_answer == "Test answer"
    assert pending_review.confidence_score == 0.75
    assert pending_review.status == ReviewStatus.PENDING
    print("  ✅ Can create instance")

    # Test 4: Inherits from Base
    assert isinstance(pending_review, Base)
    print("  ✅ Inherits from Base")

    # Test 5: Check indexes exist
    indexes = {ix.name for ix in pending_review.__table__.indexes}
    expected_indexes = {
        "ix_pending_reviews_conversation_id",
        "ix_pending_reviews_status",
    }
    assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"
    print("  ✅ Indexes exist")

    # Test 6: Relationships exist
    assert hasattr(PendingReview, "conversation")
    print("  ✅ Relationships defined")

    # Test 7: Check constraints
    constraints = {c.name for c in pending_review.__table__.constraints}
    assert "ck_pending_reviews_valid_review_status" in constraints, "Missing CHECK constraints"
    print("  ✅ CHECK constraint 'ck_pending_reviews_valid_review_status' defined")

    print("✅ PendingReview model: ALL TESTS PASSED\n")


if __name__ == "__main__":
    print("=" * 50)
    print("DATABASE MODELS SMOKE TESTS")
    print("=" * 50 + "\n")

    test_service_model()
    test_ticket_model()
    test_ticket_comment_model()
    test_document_model()
    test_document_chunk_model()
    test_ticket_documents_model()
    test_conversation_model()
    test_message_model()
    test_pending_review_model()

    print("=" * 50)
    print("ALL SMOKE TESTS PASSED ✅")
    print("=" * 50)
