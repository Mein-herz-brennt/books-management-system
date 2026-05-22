# Books Management System

A RESTful API for managing books, users, and authentication, built with **FastAPI**, **SQLAlchemy (async)**, and **PostgreSQL**.

---

## Project Overview

The Books Management System provides a backend API with the following features:

- **Books** — Create, read, update, and delete books
- **Users** — User registration and profile management
- **Authentication** — JWT-based access & refresh token flow (via `PyJWT` + `bcrypt`)
- **Database** — Async PostgreSQL via `asyncpg`; SQLite supported for local development
- **Migrations** — Database schema managed with Alembic
- **Health Check** — `GET /health` endpoint to verify API and database connectivity
- **Request Tracing** — Every request is tagged with a unique `X-Request-ID` for structured logging

---

## 🛠️ Tech Stack

| Layer          | Technology                      |
|----------------|---------------------------------|
| Framework      | FastAPI                         |
| ORM            | SQLAlchemy (async)              |
| Database       | PostgreSQL 16                   |
| Migrations     | Alembic                         |
| Auth           | PyJWT + bcrypt                  |
| Server         | Uvicorn                         |
| Testing        | Pytest + pytest-asyncio + HTTPX |
| Containerizing | Docker + Docker Compose         |

---

## Project Structure

```
books-management-system/
├── src/
│   ├── main.py           # FastAPI app entry point, middleware, logging
│   ├── api/              # Route aggregation
│   ├── core/             # Database session, config, dependencies
│   └── modules/
│       ├── auth/         # Login, token refresh, JWT logic
│       ├── books/        # Books CRUD endpoints & models
│       └── users/        # User registration & profile endpoints
├── alembic/              # Database migration scripts
├── tests/                # Automated test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
└── .env.example
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose (for the containerized setup)

---

### Option 1 — Run with Docker (Recommended)

This starts both the **PostgreSQL** database and the **API** server automatically.

```bash
# 1. Clone the repository
git clone https://github.com/Mein-herz-brennt/books-management-system.git
cd books-management-system

# 2. Build and start all services
docker-compose up --build
```

The API will be available at: **http://localhost:8000**  
Interactive docs (Swagger UI): **http://localhost:8000/docs/#/**

> Database migrations are applied automatically on container startup.

