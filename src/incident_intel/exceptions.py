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
