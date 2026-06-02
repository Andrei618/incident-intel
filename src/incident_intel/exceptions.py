"""Domain exceptions for Incident Intel.

These exceptions represent business rule violations ana are independent
of any web framework. They are caugch by the API layer and converted
to appropriate HTTP responses.
"""

from uuid import UUID


class DomainError(Exception):
    """Base exception for all domain/business logic errors."""

    pass  # No custom logic needed


class TicketNotFoundError(DomainError):
    """Exception raised when a ticket ID does not exist in the database."""

    def __init__(self, ticket_id: UUID) -> None:
        """Exception when ticket ID not found.

        API layer can access ticket ID stored in this exception:
        >>> except TicketNotFoundError as e: ... e.ticket_id
        """
        self.ticket_id = ticket_id  # for calling ticket_id argument of exception
        super().__init__(f"Ticket {ticket_id} not found")  # for calling parent method __str__


class ServiceNotFoundError(DomainError):
    """Exception raised when a service ID does not exist in the database."""

    def __init__(self, service_id: UUID) -> None:
        """Exception when service ID not found.

        API layer can access service ID stored in this exception:
        >>> except ServiceNotFoundError as e: ... e.service_id
        """
        self.service_id = service_id
        super().__init__(f"Service {service_id} not found")


class DocumentNotFoundError(DomainError):
    """Exception raised when a document ID does not exist in the database."""

    def __init__(self, document_id: UUID) -> None:
        """Exception when document ID not found.

        API layer can access document ID stored in this exception:
        >>> except DocumentNotFoundError as e: ... e.document_id
        """
        self.document_id = document_id
        super().__init__(f"Document {document_id} not found")


class BusinessRuleViolationError(DomainError):
    """Exception raised when business rules are violated."""

    def __init__(self, message: str) -> None:
        """Exception when data violates business rules.

        API layer can access message stored in this exception:
        >>> except BusinessRuleViolationError as e: ... str(e)
        """
        super().__init__(message)


class ConversationNotFoundError(DomainError):
    """Exception raised when a conversation ID does not exist in the database."""

    def __init__(self, conversation_id: UUID) -> None:
        """Exception when conversation ID not found.

        API layer can access conversation ID stored in this exception:
        >>> except ConversationNotFoundError as e: ... e.conversation_id
        """
        self.conversation_id = conversation_id
        super().__init__(f"Conversation {conversation_id} not found")
