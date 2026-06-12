"""App entry point."""

import os

from dotenv import load_dotenv

# Load environment variables BEFORE importing any local modules that read os.getenv().
# Python executes module-level code at import time, so we must load .env first.
load_dotenv()

from fastapi import FastAPI  # noqa: E402 (E402: import not at top)
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from incident_intel.api import health  # noqa: E402
from incident_intel.api.v1 import (  # noqa: E402
    chat,
    conversations,
    documents,
    search,
    services,
    tickets,
)
from incident_intel.core.logging import configure_logging  # noqa: E402
from incident_intel.middleware.request_id import RequestIDMiddleware  # noqa: E402

configure_logging()

app: FastAPI = FastAPI(
    title="Incident Intelligence Assistant",
    version="0.1.0",
    description=(
        "Assistant for IT operations teams answering questions over structured incident data"
        " and documentation using retrieval-augmented generation (RAG)."
    ),
)

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
ALLOWED_ORIGIN_REGEX = os.getenv("CORS_ALLOWED_ORIGIN_REGEX") or None

app.add_middleware(RequestIDMiddleware)

# CORSMiddleware is registered after RequestIDMiddleware because in Starlette
# middleware executes in reverse registration order
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(tickets.router, prefix="/api/v1")
app.include_router(services.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
