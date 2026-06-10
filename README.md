# TubeMind - AI-Powered YouTube Knowledge Assistant

## Project Overview
TubeMind is a sophisticated AI-powered application that transforms YouTube video content into an interactive, searchable knowledge base. Leveraging Retrieval-Augmented Generation (RAG), the system processes video transcripts, performs semantic chunking with precise timestamp preservation, and utilizes Google's Gemini Large Language Model to deliver highly accurate, context-aware responses to user queries.

## Key Technical Features
* **Advanced Content Ingestion:** Automated extraction of YouTube transcripts using robust integrations (`youtube-transcript-api` and `yt-dlp`).
* **Temporal Data Chunking:** Implementation of precision-based text chunking strategies that maintain strict alignment with video timestamps, ensuring accurate citation in responses.
* **High-Performance Vector Search:** Integration of FAISS (Facebook AI Similarity Search) for optimized, sub-second semantic retrieval of transcript data.
* **Grounded AI Responses:** Utilization of the Gemini LLM tailored via system prompts to mitigate hallucinations, ensuring answers are strictly derived from the ingested video context.
* **Stateful Data Persistence:** A PostgreSQL database backing the application to persist embeddings and video metadata, allowing stateless deployment of the vector store (rebuilt in-memory upon initialization).
* **Modern Architecture:** Built on FastAPI for asynchronous, high-throughput API endpoints, alongside a responsive, modern frontend utilizing vanilla web technologies.

## System Architecture

The application follows a modular, microservice-inspired architecture pattern:

1. **Ingestion Pipeline:** Validates URLs, extracts transcripts, chunks text, and generates vector embeddings via SentenceTransformers.
2. **Storage Layer:** PostgreSQL for relational data and persistent embedding storage; FAISS for in-memory, high-speed similarity search.
3. **Retrieval and Generation:** A custom RAG pipeline that intercepts user queries, retrieves the most relevant context vectors, and prompts the Gemini LLM for a formulated response with timestamp citations.

### Technology Stack
* **Backend Framework:** Python 3.11+, FastAPI, Uvicorn
* **Database:** PostgreSQL (asyncpg, SQLAlchemy)
* **Vector Store & Embeddings:** FAISS, SentenceTransformers (`all-MiniLM-L6-v2`)
* **Large Language Model:** Google Gemini API (`gemini-2.5-flash`)
* **Frontend Integration:** HTML5, CSS3, JavaScript
* **Infrastructure & Deployment:** Docker, Docker Compose, Render Configuration

## Local Development Setup

### Prerequisites
* Python 3.11 or higher
* PostgreSQL instance (local or remote)
* Active Google Gemini API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd tubemind
   ```

2. **Initialize a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration:**
   Copy the example environment variables and configure your specific credentials.
   ```bash
   cp .env.example .env
   ```
   Ensure `GEMINI_API_KEY` and `DATABASE_URL` are accurately populated in your `.env` file.

5. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   The API and frontend will be accessible at `http://localhost:8000`.

## Containerized Deployment

For environment consistency, the application can be run using Docker:

```bash
cp .env.example .env
docker-compose up --build
```

### Production Deployment (Render)
The repository includes a `render.yaml` configuration for streamlined deployment to the Render platform. It automatically provisions a web service instance and a PostgreSQL database. 
*Note: Ensure the `DATABASE_URL` uses the `postgresql+asyncpg://` dialect prefix in the Render environment variables.*

## API Specification

The application exposes a fully documented RESTful API. Below are the primary endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ingest` | `POST` | Processes a YouTube URL and indexes its transcript. |
| `/api/query` | `POST` | Executes a natural language query against indexed videos. |
| `/api/videos` | `GET` | Retrieves a list of all processed video resources. |
| `/api/videos/{id}` | `DELETE` | Removes a specific video and its associated embeddings. |
| `/api/health` | `GET` | Application health diagnostic endpoint. |

## Engineering Highlights
* **Stateless Vector Store Management:** The FAISS index is intentionally designed to be stateless. It rebuilds asynchronously from PostgreSQL upon application startup, reducing persistent volume requirements and simplifying cloud deployments.
* **Prompt Engineering for Hallucination Prevention:** The LLM integration includes strict boundary prompts, forcing the model to respond with "I don't know" when sufficient context is unavailable within the ingested transcripts.
* **Asynchronous Database Operations:** Leverages `asyncpg` to ensure database I/O does not block the FastAPI event loop, maximizing concurrent request handling.

## License
This project is licensed under the MIT License.
