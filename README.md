# Incident Intelligence Assistant

> AI-powered assistant for IT operations teams that intelligently queries both structured incident data and unstructured documentation using RAG (Retrieval-Augmented Generation).

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.125+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL 17](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## 🚧 Project Status

**Currently in active development** - Week 1 of 8-week implementation plan.

**Completed:**
- ✅ Project initialization and dependency management
- ✅ Docker infrastructure (PostgreSQL 17 + pgvector, Redis 7.4)
- ✅ Development environment configuration

**In Progress:**
- 🔄 Database schema and migrations
- 🔄 FastAPI application skeleton
- 🔄 Core domain models

---

## 🎯 Project Overview

This assistant helps IT operations teams by:
- **Answering questions** about past incidents using semantic search
- **Retrieving relevant documentation** from runbooks and wikis
- **Combining structured data** (tickets, incidents) with unstructured data (docs, logs)
- **Providing context-aware responses** using LangChain and LangGraph

### Tech Stack

| Category | Technology |
|----------|-----------|
| **Language** | Python 3.13+ |
| **Web Framework** | FastAPI 0.125+ |
| **Database** | PostgreSQL 17 with pgvector |
| **Cache** | Redis 7.4 |
| **AI/LLM** | LangChain, LangGraph, OpenAI |
| **Package Manager** | uv |
| **Code Quality** | Ruff, mypy, pytest |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- Docker and Docker Compose
- uv package manager ([installation guide](https://github.com/astral-sh/uv))
- OpenAI API key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/incident-intel.git
   cd incident-intel
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Start infrastructure:**
   ```bash
   docker compose up -d
   ```

4. **Install dependencies:**
   ```bash
   uv sync
   ```

5. **Verify setup:**
   ```bash
   # Check PostgreSQL
   docker exec -it incident-intel-db psql -U postgres -d incident_intel -c "SELECT version();"
   
   # Check Redis
   docker exec -it incident-intel-redis redis-cli ping
   ```

---

## 🏗️ Project Structure

```
incident-intel/
├── src/
│   └── incident_intel/      # Main application code
│       ├── api/              # FastAPI routes and endpoints
│       ├── core/             # Core business logic
│       ├── db/               # Database models and migrations
│       └── services/         # LLM and external service integrations
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── evals/                # LLM evaluation tests
├── .internal/                # Internal documentation (not committed)
│   ├── project_context/      # Project planning and context
│   └── setup_workflow/       # Setup guides and workflows
├── docker-compose.yml        # Local development infrastructure
├── pyproject.toml            # Project dependencies and configuration
└── README.md                 # This file
```

---

## 🛠️ Development

### Running the Application

```bash
# Start all services
docker compose up -d

# Run the FastAPI server (when implemented)
uv run uvicorn src.incident_intel.main:app --reload
```

### Code Quality

```bash
# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Type checking
uv run mypy src/

# Run tests
uv run pytest
```

### Database Management

```bash
# Run migrations (when implemented)
uv run alembic upgrade head

# Create a new migration
uv run alembic revision --autogenerate -m "description"
```

---

## 📚 Documentation

- **Setup Guide:** `.internal/setup_workflow/project-initialization.md`
- **Docker Guide:** `.internal/setup_workflow/docker-setup.md`
- **Implementation Plan:** `.internal/project_context/IMPLEMENTATION_PLAN.md`
- **AI Context:** `.internal/project_context/ai-context.md`

---

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/ --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_example.py
```

---

## 🚀 Deployment

Deployment to Railway (coming soon):
- PostgreSQL with pgvector extension
- Redis for caching
- FastAPI application
- Environment-based configuration

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🤝 Contributing

This is a portfolio project and not currently accepting contributions. However, feel free to fork and adapt for your own use!

---

## 📧 Contact

**Andrei** - [GitHub Profile](https://github.com/YOUR_USERNAME)

---

**Note:** This project is part of a portfolio demonstrating full-stack AI application development with modern Python tools and best practices.
