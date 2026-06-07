---
title: TubeMind Backend
emoji: 🎬
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: AI-powered YouTube Q&A using RAG, FastAPI & Gemini
---

# TubeMind


**AI-powered understanding for every YouTube video.**

TubeMind is an AI-powered YouTube knowledge assistant that transforms videos into searchable, interactive conversations using Retrieval-Augmented Generation (RAG).

Paste a YouTube URL, and TubeMind extracts the transcript, chunks it with timestamps, embeds it into a vector store, and lets you ask natural language questions with grounded answers and timestamp citations.

![TubeMind](https://img.shields.io/badge/AI-TubeMind-purple?style=for-the-badge) ![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?style=for-the-badge)

---

## Features

- **YouTube URL Ingestion** — Paste any YouTube link to extract its transcript
- **Temporal Chunking** — Transcript is chunked with timestamp preservation
- **Semantic Search** — FAISS-powered vector similarity search
- **Grounded Answers** — Gemini generates answers strictly from transcript context
- **Timestamp Citations** — Every answer includes clickable `[MM:SS]` citations
- **Multi-Video Querying** — Ask questions across all ingested videos
- **Premium UI** — Dark glassmorphism design with smooth animations

---

## Architecture

```
User -> FastAPI -> Ingestion Pipeline -> FAISS + PostgreSQL
                                           |
User -> FastAPI -> Retriever -> Gemini LLM -> Grounded Answer + Citations
```

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Uvicorn |
| LLM | Google Gemini (gemini-2.5-flash) |
| Embeddings | SentenceTransformers (all-MiniLM-L6-v2) |
| Vector Store | FAISS (in-memory, rebuilt from PostgreSQL) |
| Database | PostgreSQL (asyncpg + SQLAlchemy) |
| Transcripts | youtube-transcript-api + yt-dlp |
| Frontend | Vanilla HTML/CSS/JS |
| Deployment | Docker + Render |

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (local or cloud)
- [Gemini API Key](https://aistudio.google.com/)

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd tubemind

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
# Edit .env with your GEMINI_API_KEY and DATABASE_URL
```

### 3. Run

```bash
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** in your browser.

---

## Docker

```bash
# Copy and configure .env
copy .env.example .env

# Start app + PostgreSQL
docker-compose up --build
```

---

## Deploy to Render

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click **New > Blueprint** and connect your repo
4. Render will read `render.yaml` and create:
   - Web service (Docker)
   - PostgreSQL database
5. Set `GEMINI_API_KEY` in the Render environment variables
6. **Important**: Update `DATABASE_URL` to use `postgresql+asyncpg://` prefix instead of `postgresql://`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ingest` | Ingest a YouTube video |
| `POST` | `/api/query` | Ask a question |
| `GET` | `/api/videos` | List ingested videos |
| `DELETE` | `/api/videos/{id}` | Delete a video |
| `GET` | `/api/health` | Health check |

### Example: Ingest a Video

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

### Example: Ask a Question

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main topics discussed?", "video_id": "VIDEO_ID"}'
```

---

## Project Structure

```
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Settings
│   ├── api/                    # API endpoints
│   ├── ingestion/              # Transcript extraction & processing
│   ├── embeddings/             # SentenceTransformer wrapper
│   ├── vectorstore/            # FAISS index management
│   ├── rag/                    # RAG pipeline & Gemini integration
│   ├── db/                     # PostgreSQL models & connection
│   └── middleware/             # Logging & error handling
├── frontend/                   # HTML/CSS/JS UI
├── Dockerfile
├── docker-compose.yml
├── render.yaml
└── requirements.txt
```

---

## Key Engineering Concepts

- **Temporal Chunking** — Preserves video timestamps for citation accuracy
- **FAISS Rebuild from PostgreSQL** — Stateless deployment: FAISS index rebuilt on startup from DB-stored embeddings
- **Grounded Generation** — System prompt forces LLM to answer only from provided context
- **Hallucination Prevention** — "I don't know" responses when context is insufficient

---

## License

MIT
