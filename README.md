# Incident Intelligence Assistant

> AI-powered assistant for IT operations teams that intelligently queries both structured incident data and unstructured documentation using RAG (Retrieval-Augmented Generation).

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.125+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL 17](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## 🚧 Status

**Current Phase:** Active Development

This project demonstrates a production-ready FastAPI application with modern Python tooling and AI/RAG capabilities.

**Implemented:**
- RESTful CRUD APIs with FastAPI
- Async SQLAlchemy with PostgreSQL + pgvector
- Structured logging with request correlation
- Comprehensive test coverage
- Code quality automation (ruff, mypy, pre-commit)

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
| **Logging** | structlog (structured JSON logging with request correlation) |
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
   git clone https://github.com/Andrei618/incident-intel.git
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

6. **Install pre-commit hooks:**
   ```bash
   uv run pre-commit install
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
uv run uvicorn incident_intel.main:app --reload --host 0.0.0.0 --port 8000
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

### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to automatically check code quality before commits.

**Setup (one-time):**
```bash
# Install pre-commit hooks
uv run pre-commit install
```

**Usage:**
```bash
# Hooks run automatically on git commit
git commit -m "your message"

# Run manually on all files
uv run pre-commit run --all-files

# Run manually on staged files only
uv run pre-commit run
```

**What gets checked:**
- ✅ Ruff linting (with auto-fix)
- ✅ Ruff formatting
- ✅ Mypy type checking (strict mode)

**Note:** If hooks fail, the commit is blocked. Fix the issues and try again.

### Database Management

```bash
# Run migrations (when implemented)
uv run alembic upgrade head

# Create a new migration
uv run alembic revision --autogenerate -m "description"
```

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

**Andrei** - [GitHub Profile](https://github.com/Andrei618)

---

**Note:** This project is part of a portfolio demonstrating full-stack AI application development with modern Python tools and best practices.
