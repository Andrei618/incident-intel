"""Unit tests for document service."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.exceptions import DocumentNotFoundError, ServiceNotFoundError
from incident_intel.models.document import DocType
from incident_intel.models.service import Service
from incident_intel.schemas.document import DocumentCreate, DocumentUpdate
from incident_intel.services.document_service import (
    create_document,
    delete_document,
    get_document,
    list_documents,
    update_document,
)


# ============== create_document ===================
async def test_create_document_success(test_session: AsyncSession, sample_service: Service) -> None:
    """Test document service can create a document."""
    # Arrange
    data = DocumentCreate(
        service_id=sample_service.id,
        title="Test title",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )
    # Act
    created_document = await create_document(session=test_session, data=data)

    # Assert
    assert created_document.id is not None
    assert created_document.service_id == sample_service.id
    assert created_document.title == "Test title"
    assert created_document.content == "Test content"
    assert created_document.doc_type == DocType.RUNBOOK


async def test_create_document_nonexistent_service_raises_service_not_found(
    test_session: AsyncSession,
) -> None:
    """Test document service raises ServiceNotFoundError for nonexistent service.

    FK violation: Raises ServiceNotFoundError when creating a document with invalid service_id.
    """
    # Arrange
    data = DocumentCreate(
        service_id=uuid.uuid4(),
        title="Test title",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )

    # Act
    with pytest.raises(ServiceNotFoundError) as exc_info:
        await create_document(session=test_session, data=data)

    # Assert
    assert exc_info.value.service_id == data.service_id


# ============== get_document ===================
async def test_get_document_success(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test document service can get existing document."""
    # Arrange
    data = DocumentCreate(
        service_id=sample_service.id,
        title="Test title",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )
    created_document = await create_document(session=test_session, data=data)

    # Act
    fetched_document = await get_document(session=test_session, document_id=created_document.id)

    # Assert
    assert fetched_document.id == created_document.id


async def test_get_document_nonexistent_document_raises_document_not_found(
    test_session: AsyncSession,
) -> None:
    """Test document service raises DocumentNotFoundError for nonexisting document.

    Raises DocumentNotFoundError when fetching a document that does not exist.
    """
    # Arrange
    nonexistent_id = uuid.uuid4()

    # Act
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await get_document(session=test_session, document_id=nonexistent_id)

    # Assert
    assert exc_info.value.document_id == nonexistent_id


# ============== update_document ===================
async def test_update_document_success(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test document service can update document."""
    # Arrange
    data = DocumentCreate(
        service_id=sample_service.id,
        title="Test title",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )
    created_document = await create_document(session=test_session, data=data)
    update_data = DocumentUpdate(title="Updated title")

    # Act
    updated_document = await update_document(
        session=test_session,
        document_id=created_document.id,
        update_data=update_data,
    )

    # Assert
    assert updated_document.title == "Updated title"


async def test_update_document_empty_update(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test document service makes no update when update data were not provided."""
    # Arrange
    data = DocumentCreate(
        service_id=sample_service.id,
        title="Test",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )
    created_document = await create_document(
        session=test_session,
        data=data,
    )
    update_data = DocumentUpdate()

    # Act
    updated_document = await update_document(
        session=test_session,
        document_id=created_document.id,
        update_data=update_data,
    )

    # Assert
    assert updated_document.id == created_document.id
    assert updated_document.service_id == sample_service.id
    assert updated_document.title == "Test"
    assert updated_document.content == "Test content"
    assert updated_document.doc_type == DocType.RUNBOOK


async def test_update_document_nonexistent_document_raises_document_not_found(
    test_session: AsyncSession,
) -> None:
    """Test document service raises DocumentNotFoundError for nonexisting document."""
    # Arrange
    nonexisting_id = uuid.uuid4()
    update_data = DocumentUpdate(title="Updated title")

    # Act
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await update_document(
            session=test_session,
            document_id=nonexisting_id,
            update_data=update_data,
        )

    # Assert
    assert exc_info.value.document_id == nonexisting_id


async def test_update_document_nonexistent_service_raises_service_not_found(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test document service raises ServiceNotFoundError for nonexisting service."""
    # Arrange
    data = DocumentCreate(
        service_id=sample_service.id,
        title="Test",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )
    created_document = await create_document(
        session=test_session,
        data=data,
    )

    nonexisting_service_id = uuid.uuid4()
    update_data = DocumentUpdate(
        service_id=nonexisting_service_id,
        title="Updated title",
    )

    # Act
    with pytest.raises(ServiceNotFoundError) as exc_info:
        await update_document(
            session=test_session,
            document_id=created_document.id,
            update_data=update_data,
        )

    # Assert
    assert exc_info.value.service_id == nonexisting_service_id


# ============== list_document ===================
async def test_list_documents_no_filters(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test document service can return list of all existing documents.

    Without filters and pagination arguments it returns the full list of documents.
    """
    # Arrange
    data_1 = DocumentCreate(
        service_id=sample_service.id,
        title="Test_1",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )
    data_2 = DocumentCreate(
        service_id=sample_service.id,
        title="Test_2",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )
    await create_document(session=test_session, data=data_1)
    await create_document(session=test_session, data=data_2)

    # Act
    documents, total = await list_documents(session=test_session)

    # Assert
    assert len(documents) == 2
    assert total == 2


async def test_list_documents_filter_by_service_id(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test document service filters list of documnets by service_id."""
    # Arrange
    # Create document 1
    service_id_1 = sample_service.id
    data_1 = DocumentCreate(
        service_id=service_id_1,
        title="Test_1",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )
    await create_document(session=test_session, data=data_1)

    # Create document 2
    service_2 = Service(name="test_service_2")
    test_session.add(service_2)
    await test_session.commit()
    await test_session.refresh(service_2)

    data_2 = DocumentCreate(
        service_id=service_2.id,
        title="Test_2",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )
    await create_document(session=test_session, data=data_2)

    # Act
    documents, total = await list_documents(
        session=test_session,
        service_id=service_id_1,
    )

    # Assert
    assert len(documents) == 1
    assert total == 1
    assert documents[0].title == "Test_1"


async def test_list_documents_filter_by_doc_type(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test document service filters list of documents by doc_type."""
    # Arrange
    # Create document 1
    data_1 = DocumentCreate(
        service_id=sample_service.id,
        title="Test_1",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )
    await create_document(session=test_session, data=data_1)

    # Create document 2
    data_2 = DocumentCreate(
        service_id=sample_service.id,
        title="Test_2",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )
    created_document_2 = await create_document(session=test_session, data=data_2)

    # Change doc_type of document 2 to POLICY
    update_data = DocumentUpdate(doc_type=DocType.POLICY)
    await update_document(
        session=test_session,
        document_id=created_document_2.id,
        update_data=update_data,
    )
    # Act
    documents, total = await list_documents(
        session=test_session,
        doc_type=DocType.RUNBOOK,
    )

    # Assert
    assert len(documents) == 1
    assert total == 1
    assert documents[0].title == "Test_1"


async def test_list_documents_filter_by_title_search(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test document service filters list of documents by search in title (case-insensitive)."""
    # Arrange
    test_documents = [
        ("Database Backup and Recovery Procedures", DocType.RUNBOOK),
        ("BACKUP Schedule for Production Systems", DocType.POLICY),
        ("Disaster Recovery Planning Template", DocType.GUIDE),
    ]
    created_documents = []
    for title, doc_type in test_documents:
        created_document = await create_document(
            session=test_session,
            data=DocumentCreate(
                service_id=sample_service.id,
                title=title,
                content="Test content",
                doc_type=doc_type,
            ),
        )
        created_documents.append(created_document)

    # Act
    documents, total = await list_documents(
        session=test_session,
        title_search="backup",
    )

    # Assert
    assert len(documents) == 2
    assert total == 2
    # Verify the matching titles
    matched_titles = {doc.title for doc in documents}
    assert "Database Backup and Recovery Procedures" in matched_titles
    assert "BACKUP Schedule for Production Systems" in matched_titles
    # Verify the non-match is excluded
    assert "Disaster Recovery Planning Template" not in matched_titles


async def test_list_documents_empty(
    test_session: AsyncSession,
) -> None:
    """Test document service return empty list when no documents exist."""
    # Act
    documents, total = await list_documents(session=test_session)

    # Assert
    assert len(documents) == 0
    assert total == 0


async def test_list_documents_pagination(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test document service returns list of documents with limit and offset."""
    # Arrange
    titles = ("Title 1", "Title 2", "Title 3")
    test_documents = []
    for title in titles:
        created_document = await create_document(
            session=test_session,
            data=DocumentCreate(
                service_id=sample_service.id,
                title=title,
                content="Test content",
                doc_type=DocType.RUNBOOK,
            ),
        )
        test_documents.append(created_document)

    # Act 1
    documents, total = await list_documents(
        session=test_session,
        limit=2,
        offset=0,
    )

    # Assert 1
    assert len(documents) == 2
    assert total == 3

    # Act 2
    documents, total = await list_documents(
        session=test_session,
        limit=2,
        offset=2,
    )

    # Assert 2
    assert len(documents) == 1
    assert total == 3


# ============== delete_document ===================
async def test_delete_document_success(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test document service deletes document by ID."""
    # Arrange
    data = DocumentCreate(
        service_id=sample_service.id,
        title="Test",
        content="Test content",
        doc_type=DocType.RUNBOOK,
    )
    created_document = await create_document(session=test_session, data=data)

    # Act
    await delete_document(session=test_session, document_id=created_document.id)

    # Assert
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await get_document(session=test_session, document_id=created_document.id)

    assert exc_info.value.document_id == created_document.id


async def test_delete_document_nonexistent_document_raises_document_not_found(
    test_session: AsyncSession,
) -> None:
    """Test document service raises DocumentNotFoundError for nonexisting documentf."""
    # Arrange
    nonexisting_id = uuid.uuid4()

    # Act
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await delete_document(session=test_session, document_id=nonexisting_id)

    # Assert
    assert exc_info.value.document_id == nonexisting_id
