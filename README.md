# TruthLens 🔍 — AI-Powered Social Media Fact-Checking Platform

> **An evidence-backed, multi-modal verification platform that automatically analyzes claims from social media posts, searches authoritative sources, and synthesizes nuanced veracity reports.**

---

## 🌟 Key Features

- **Multi-Modal Claim Extraction**: Ingests social media posts (Instagram, Facebook, etc.) and extracts falsifiable factual claims from text, OCR-extracted text, and visual elements using Groq-accelerated LLMs.
- **Evidence Search & Ranking**: Queries authoritative web sources (DuckDuckGo, Brave, Serper, Tavily) and scores evidence relevance with zero hallucination bias.
- **Automated Reasoning Engine**: Evaluates evidence against claims with structured confidence ratings (`SUPPORTED`, `CONTRADICTED`, `MISLEADING`, `INSUFFICIENT_EVIDENCE`).
- **Complete Authentication Flow**: Secure user registration, JWT-based login, profile state persistence, and logout with bcrypt hashing and PostgreSQL.
- **Polished Modern UI**: Built with React, Tailwind CSS, and Lucide icons featuring a deep violet/indigo and amber palette, elapsed time trackers, and step-by-step pipeline inspection.

---

## 🏗️ Architecture

```
┌───────────────────────────────────────────────────────────┐
│               Frontend (React + Vite + Tailwind)          │
│        - Home & Demo Analysis  - Dynamic Verification     │
│        - Auth Flow (JWT)       - Detailed Evidence Report │
└─────────────────────────────┬─────────────────────────────┘
                              │ HTTP / JSON API
┌─────────────────────────────▼─────────────────────────────┐
│                 TruthLens Backend (FastAPI)               │
│                                                           │
│  [Auth Router]   [Analysis Router]    [Scraper Service]   │
│   (JWT/Bcrypt)    (Multi-Stage)       (Apify / Ingestion) │
│         │                 │                               │
│  [PostgreSQL / DB] [Vision Analysis]  [Evidence Search]   │
│   (SQLAlchemy)      (Groq Multimodal)   (Search Providers)│
└───────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+ & npm**
- **PostgreSQL 14+** (or local async fallback)

---

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials, GROQ_API_KEY, and APIFY tokens:
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/truthlens
# JWT_SECRET_KEY=your_secure_jwt_secret_key

# Start backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend API will be live at `http://localhost:8000`. Swagger documentation is available at `http://localhost:8000/docs`.

---

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

The application will be running at `http://localhost:5173` (or `http://localhost:5174`).

---

## Deploy Backend to Railway

The backend is packaged in `backend/Dockerfile` and is ready to run as a Railway service.

### 1. Create the services

1. Create a new Railway project and add a **PostgreSQL** service.
2. Add this repository as a second service.
3. In the backend service settings, set **Root Directory** to `/backend`.
    Railway will use `backend/railway.toml` and `backend/Dockerfile`.

### 2. Configure variables

In the backend service, add the following variables. Railway's PostgreSQL service exposes the connection URL through a service reference:

```ini
DATABASE_URL=${{Postgres.DATABASE_URL}}
JWT_SECRET_KEY=<long-random-secret>
GROQ_API_KEY=<your-groq-key>
APIFY_API_TOKEN=<your-apify-token>
APIFY_INSTAGRAM_ACTOR=apify/instagram-scraper
APIFY_FACEBOOK_ACTOR=apify/facebook-posts-scraper
CORS_ORIGINS=["https://<your-frontend-domain>"]
FRONTEND_URL=https://<your-frontend-domain>
```

The frontend service must also define this build-time variable before deploying:

```ini
VITE_API_URL=https://<your-backend-domain>/api
VITE_USE_MOCK_API=false
```

The backend accepts Railway's `postgres://`, `postgresql://`, and `postgresql+asyncpg://` URL forms. Database tables are created during application startup. Railway supplies `PORT` automatically; the Docker image uses it and falls back to port `8000` for local runs. `FRONTEND_URL` must contain only the frontend origin, without `/api`; `VITE_API_URL` must contain the backend origin plus `/api`.

After deployment, verify `https://<backend-domain>/health` returns a JSON response with `"status": "ok"`. Set the frontend's `VITE_API_URL` to `https://<backend-domain>/api` and redeploy the frontend.

---

## 🔐 Authentication Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/signup` | Register a new user (`name`, `email`, `password >= 6 chars`) |
| `POST` | `/api/v1/auth/login` | Authenticate user and receive JWT access token |
| `GET` | `/api/v1/auth/me` | Retrieve profile of authenticated user (`Bearer <token>`) |
| `POST` | `/api/v1/auth/logout` | Invalidate session |

---

## 🛡️ Core Verification Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check endpoint |
| `POST` | `/api/v1/analyze` | Full social media post analysis pipeline |

---

## 🗄️ Database & Environment Variables

### Backend (`backend/.env`)
```ini
# PostgreSQL connection string
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/truthlens

# JWT Security
JWT_SECRET_KEY=your_super_secret_jwt_key_here

# Groq LLM API
GROQ_API_KEY=gsk_your_groq_api_key_here

# Apify Social Media Scraper (Optional for live URLs)
APIFY_API_TOKEN=your_apify_api_token_here
APIFY_INSTAGRAM_ACTOR=apify/instagram-scraper
APIFY_FACEBOOK_ACTOR=apify/facebook-posts-scraper
```

### Frontend (`frontend/.env`)
```ini
VITE_API_URL=http://localhost:8000/api
VITE_USE_MOCK_API=false
```

---

## 📄 License

This project is licensed under the MIT License.
# TruthLens
Full-stack AI fact-checking engine built with FastAPI, PostgreSQL, Groq LLMs, and React. Evaluates multi-modal claims from social media with real-time web evidence ranking and verifiable truth reports.
