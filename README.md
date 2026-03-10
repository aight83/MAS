# MAS RAG System

A Multi-Agent System with Retrieval-Augmented Generation (RAG) that combines AI agents with vector-based document retrieval.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed

### Startup

To start the entire application stack, run:

```bash
docker compose up --build
```

The `--build` flag ensures all services are built with the latest changes.

> **Note:** The first startup may take a few minutes as all services initialize and the ingest process populates the vector database.

## Accessing Services

Once the application is running, you can access the following services on your local machine:

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:8501 | Streamlit web interface - Main application UI |
| **Backend API** | http://localhost:8000 | FastAPI server - API endpoints and documentation |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger UI for API testing |
| **MongoDB Admin** | http://localhost:8081 | Mongo Express - MongoDB database management (To see history of chats) |
| **Vector Database** | http://localhost:6333 | Qdrant - Vector store for RAG |
| **PostgreSQL** | localhost:5432 | PostgreSQL database - For text2sql agent |
| **MongoDB** | localhost:27017 | MongoDB - Stores conversation history and user memory |

## Services Overview

### Frontend (Port 8501)
- **Technology:** Streamlit
- **Purpose:** User-friendly web interface for the MAS RAG system
- **Access:** http://localhost:8501

### Backend (Port 8000)
- **Technology:** FastAPI
- **Purpose:** REST API for agent orchestration and RAG queries
- **API Documentation:** http://localhost:8000/docs

### Databases
- **PostgreSQL (5432):** For text2sql agent
- **MongoDB (27017):** Stores conversation history and user memory
- **Qdrant (6333):** Vector database for semantic search and RAG

### Admin Interfaces
- **Mongo Express (8081):** Web UI for MongoDB management
- **Qdrant (6333):** API for vector storage operations

## Stopping the Application

To stop all services:

```bash
docker compose down
```

To stop and remove all data (volumes):

```bash
docker compose down -v
```

## Configuration

### Setting up Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit the `.env` file and fill in your credentials:
   - **AWS credentials:** Your AWS access key and secret key
   - **AI Studio API Key:** Your API key for AI studio services
   - **Database credentials:** PostgreSQL and MongoDB passwords (can use defaults for local development)

The `.env` file should contain:
- Database credentials
- MongoDB connection strings
- API keys and authentication
- Backend URLs

The `.env.example` file is provided as a template with placeholder values marked as `...` for sensitive credentials that need to be configured.

## Data

Input data files should be placed in the `data/` directory. These will be ingested into the vector database on startup.

## Troubleshooting

- **Services not responding:** Wait a few seconds for all services to fully initialize, especially PostgreSQL (which has a health check)
- **Port already in use:** Change the port mappings in `docker-compose.yml` if needed
- **Database connection errors:** Ensure `.env` file is properly configured with database credentials
