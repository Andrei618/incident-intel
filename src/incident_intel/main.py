"""App entry point."""

from fastapi import FastAPI

from incident_intel.api import health

app: FastAPI = FastAPI(
    title="Incident Intelligence Assistant",
    version="0.1.0",
    description="AI-powered assistant for IT operations teams that intelligently queries both structured incident data and unstructured documentation using RAG"
)

app.include_router(health.router)
