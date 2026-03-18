"""App entry point."""

from dotenv import load_dotenv

# Load environment variables BEFORE importing any local modules that read os.getenv().
# Python executes module-level code at import time, so we must load .env first.
load_dotenv()

from fastapi import FastAPI  # noqa: E402, I001 //E402: import not at top, I001: import block is unsorted

from incident_intel.api import health  # noqa: E402
from incident_intel.api.v1 import chat, documents, search, tickets  # noqa: E402
from incident_intel.core.logging import configure_logging  # noqa: E402
from incident_intel.middleware.request_id import RequestIDMiddleware  # noqa: E402

configure_logging()

app: FastAPI = FastAPI(
    title="Incident Intelligence Assistant",
    version="0.1.0",
    description=(
        "AI-powered assistant for IT operations teams that intelligently queries "
        "both structured incident data and unstructured documentation using RAG"
    ),
)

app.add_middleware(RequestIDMiddleware)

app.include_router(health.router)
app.include_router(tickets.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
