# FraudLens Architecture, Operational Guide & Engineering Rationale

> **FraudLens** is an explainable, human-in-the-loop (HITL) fraud review assistant designed for small fintechs and e-commerce platforms. It scores incoming transactions using an XGBoost classifier, explains risk scores using SHAP values and an LLM agent, and presents actionable insights to human analysts who retain final approval authority.

---

## Table of Contents
1. [Core Philosophy & System Principles](#1-core-philosophy--system-principles)
2. [Step-by-Step Operational Guide (How to Run Everything)](#2-step-by-step-operational-guide-how-to-run-everything)
   - [2.1 Local Development Mode](#21-local-development-mode)
   - [2.2 Data Generation & Model Training Pipeline](#22-data-generation--model-training-pipeline)
   - [2.3 Containerized Execution (Docker & Docker Compose)](#23-containerized-execution-docker--docker-compose)
   - [2.4 Test & Quality Assurance Suite](#24-test--quality-assurance-suite)
   - [2.5 Cloud Deployment Strategies](#25-cloud-deployment-strategies)
3. [Backend Engineering & Rationale](#3-backend-engineering--rationale)
   - [3.1 FastAPI & Async Execution](#31-fastapi--async-execution)
   - [3.2 Database Strategy (SQLite & PostgreSQL Dual-Mode)](#32-database-strategy-sqlite--postgresql-dual-mode)
   - [3.3 Security, JWT Auth & Rate Limiting](#33-security-jwt-auth--rate-limiting)
   - [3.4 Observability (Prometheus Instrumentation)](#34-observability-prometheus-instrumentation)
4. [Machine Learning & Explainability Engine](#4-machine-learning--explainability-engine)
   - [4.1 Model Selection (XGBoost)](#41-model-selection-xgboost)
   - [4.2 Metric Selection: PR-AUC vs Accuracy](#42-metric-selection-pr-auc-vs-accuracy)
   - [4.3 Threshold Optimization (Max F1 Score)](#43-threshold-optimization-max-f1-score)
   - [4.4 SHAP TreeExplainer Rationale](#44-shap-treeexplainer-rationale)
5. [LLM Agent & Decision Support Flow](#5-llm-agent--decision-support-flow)
   - [5.1 LangGraph 4-Node Orchestration](#51-langgraph-4-node-orchestration)
   - [5.2 Resilient Fallback Architecture](#52-resilient-fallback-architecture)
6. [Frontend Architecture & UX Engineering](#6-frontend-architecture--ux-engineering)
   - [6.1 Tech Stack & Code-Splitting](#61-tech-stack--code-splitting)
   - [6.2 Tailwind v4 Design System & Visual Aesthetics](#62-tailwind-v4-design-system--visual-aesthetics)
   - [6.3 Custom SVG Gauge & Visualizations](#63-custom-svg-gauge--visualizations)
7. [Database Schema & Data Lifecycle](#7-database-schema--data-lifecycle)
8. [Comprehensive File & Directory Breakdown](#8-comprehensive-file--directory-breakdown)

---

## 1. Core Philosophy & System Principles

### Human-in-the-Loop (HITL) Decision Support
Fraud detection in financial tech cannot rely on automated binary decisions for borderline cases. False positives block legitimate customers, while false negatives cause direct monetary loss. **FraudLens acts strictly as decision support, not an automated blocker.**
- The ML model calculates risk probabilities and categorizes cases into high, medium, or low risk.
- The system presents clear evidence (SHAP attribution + natural language summary).
- The **human reviewer** makes the binding decision (Approve, Reject, or Escalate).

### Transparency Over Black-Box AI
In regulatory contexts (e.g., FCRA, GDPR explanation rights), automated scoring must be explainable. FraudLens combines quantitative attribution (SHAP feature impacts) with narrative generation (LangGraph agent summary) so reviewers understand *why* a transaction was flagged in seconds.

---

## 2. Step-by-Step Operational Guide (How to Run Everything)

### 2.1 Local Development Mode

#### Prerequisites
- **Python**: `3.11+` (Virtual environment recommended)
- **Node.js**: `v18+` & `npm`

#### Step 1: Virtual Environment Setup & Backend Installation
```bash
# Clone repository and navigate to root
cd "assessment project"

# Create Python virtual environment
python -m venv venv

# Activate environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# On Linux/macOS: source venv/bin/activate

# Install dependencies (bcrypt==4.0.1 is pinned for passlib compatibility)
pip install -r requirements.txt
```

#### Step 2: Initialize Database & Model Artifacts
```bash
# Generate synthetic dataset (50,000 transactions, 300 customers)
python scripts/generate_data.py

# Train XGBoost model, calculate SHAP values, select threshold, save artifacts
python scripts/train.py

# Pre-score demo cases for instantaneous UI loading
python scripts/precompute_demo.py
```

#### Step 3: Launch Backend Server
```bash
# Run FastAPI server on port 8000
uvicorn backend.app.main:app --reload --port 8000
```
- Interactive OpenAPI Docs: `http://localhost:8000/api/docs`
- Health Check: `http://localhost:8000/health`

#### Step 4: Launch Frontend Application
Open a second terminal window:
```bash
cd frontend
npm install
npm run dev -- --port 5173
```
- Web Application: `http://localhost:5173`

#### Demo Credentials
| Role | Email | Password |
|---|---|---|
| Senior Reviewer (Admin) | `admin@fraudlens.com` | `admin123` |
| Analyst (Reviewer) | `analyst@fraudlens.com` | `analyst123` |

---

### 2.2 Data Generation & Model Training Pipeline

You can re-run the full ML generation and training pipeline at any time:

```bash
# 1. Regenerate synthetic raw transactions
python scripts/generate_data.py

# 2. Re-train XGBoost, evaluate PR-AUC, auto-select optimal F1 decision threshold
python scripts/train.py

# 3. Seed database & re-calculate demo case explanations
python scripts/precompute_demo.py
```

*Reasoning*: Separating data generation, model training, and database precomputation keeps the startup time fast while allowing complete reproducibility.

---

### 2.3 Containerized Execution (Docker & Docker Compose)

#### Option A: Single Multi-Stage Production Container
FraudLens includes a multi-stage `Dockerfile` that packages both the React static frontend build and the FastAPI backend into a single lightweight runnable image.

```bash
# Build Docker image
docker build -t fraudlens:latest .

# Run container binding port 8000
docker run -d -p 8000:8000 -e SECRET_KEY="prod_secret_key" --name fraudlens_app fraudlens:latest
```
Access application at `http://localhost:8000`.

#### Option B: Full Stack Orchestration (Docker Compose)
`docker-compose.yml` orchestrates the app alongside PostgreSQL:

```bash
# Start FraudLens app with PostgreSQL database
docker-compose up --build -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

To enable local LLM summaries via Ollama inside docker-compose:
1. Uncomment the `ollama` service block in `docker-compose.yml`.
2. Set `OLLAMA_BASE_URL=http://ollama:11434` in the app service environment.

---

### 2.4 Test & Quality Assurance Suite

Run the full pytest suite covering authentication, risk scoring, simulation endpoints, threshold management, and authorization:

```bash
# Run backend API unit and integration tests
pytest backend/tests/test_api.py -v
```

Run frontend type safety check & build validation:
```bash
cd frontend
npm run build
```

---

### 2.5 Cloud Deployment Strategies

#### Deployment to Render (Web Service)
1. Fork or push repository to GitHub.
2. Create a **New Web Service** on Render connected to your repository.
3. Configuration settings:
   - **Environment**: Docker
   - **Region**: Oregon (or closest)
   - **Plan**: Free / Starter
   - **Environment Variables**:
     - `SECRET_KEY`: Set to a secure random string (e.g., `openssl rand -hex 32`)
     - `OLLAMA_ENABLED`: `false` (uses fast deterministic fallback summaries)

#### Deployment to Hugging Face Spaces (Docker Space)
1. Create a new Space on Hugging Face and select **Docker** SDK.
2. Push the codebase to HF Space git remote:
```bash
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/fraudlens
git push hf main
```
3. The Space will automatically build `Dockerfile` and expose port 8000.

---

## 3. Backend Engineering & Rationale

### 3.1 FastAPI & Async Execution
- **Why FastAPI?**: Offers native async execution, high performance (Uvicorn / Starlette foundation), automatic JSON schema validation via Pydantic, and automatic Swagger OpenAPI documentation at `/api/docs`.
- **Lifespan Manager (`backend/app/main.py`)**: Uses Starlette `lifespan` context manager to handle startup tasks (database table auto-creation, seeding demo accounts, and warming up the ML model singleton into memory) prior to accepting HTTP connections.

### 3.2 Database Strategy (SQLite & PostgreSQL Dual-Mode)
- **Zero-Dependency Default (SQLite)**: Out-of-the-box local development and demo runs require zero external DB daemon setup. SQLite stores state in `fraudlens.db`.
- **Production Readiness (PostgreSQL)**: Driven by `DATABASE_URL` env variable in `core/config.py`. Switching from SQLite to PostgreSQL is accomplished by passing `DATABASE_URL=postgresql://user:pass@host:5432/dbname`. SQLAlchemy handles dialect abstractions transparently.

### 3.3 Security, JWT Auth & Rate Limiting
- **Password Hashing**: Implemented in `core/security.py` using `passlib.context.CryptContext` with `bcrypt`. 
  - *Critical Pinning Note*: `bcrypt==4.0.1` is strictly pinned in `requirements.txt`. Rust-backed `bcrypt` 5.x broke passlib compatibility; 4.0.1 maintains stable runtime guarantees.
- **Stateless Authentication**: Uses HMAC-SHA256 JWT tokens with configurable expiration (`ACCESS_TOKEN_EXPIRE_MINUTES=480`).
- **Sliding Window Rate Limiter**: `api/auth.py` maintains an in-memory timestamp sliding-window dictionary restricting login attempts to **5 requests per minute per IP address**, mitigating brute-force password guessing attacks.

### 3.4 Observability (Prometheus Instrumentation)
- **Monitoring (`core/monitoring.py`)**: Integrated `prometheus_client` counters and histograms:
  - `http_requests_total`: Tracks requests by endpoint and HTTP status code.
  - `scoring_duration_seconds`: Histogram measuring ML model inference + SHAP computation latency.
  - `decisions_total`: Tracks reviewer actions (Approve / Reject / Escalate).
  - `llm_calls_total`: Tracks LLM agent invocation success and fallback execution.
- Metrics are exposed at `/metrics` for scraping by Prometheus.

---

## 4. Machine Learning & Explainability Engine

### 4.1 Model Selection (XGBoost)
- **Why XGBoost over Deep Learning or Logistic Regression?**: Tabular financial fraud data is dominated by non-linear interactions between feature pairs (e.g., high transaction amount combined with an unverified IP address and high 24-hour velocity). XGBoost gradient boosted decision trees outperform neural networks on tabular datasets while requiring less training data and retaining deterministic TreeExplainer support.

### 4.2 Metric Selection: PR-AUC vs Accuracy
- **Why PR-AUC instead of Accuracy?**: Fraud datasets are heavily class-imbalanced (~2% fraud, 98% legitimate). A dummy model predicting "legitimate" for all transactions achieves 98% accuracy but 0% recall on fraud.
- FraudLens measures **Precision-Recall Area Under Curve (PR-AUC)** and **ROC-AUC** on test sets (`artifacts/metrics.json`) to evaluate class discrimination independent of decision thresholds.

### 4.3 Threshold Optimization (Max F1 Score)
- Standard binary classifiers default to `0.5` risk threshold. In fraud prevention, `0.5` is often sub-optimal depending on business risk tolerance.
- During `scripts/train.py`, FraudLens evaluates F1-scores across 100 candidate thresholds from `0.01` to `0.99` on the validation set, choosing the threshold that maximizes `F1 = 2 * (Precision * Recall) / (Precision + Recall)`.
- **Live Threshold Slider**: Reviewers can preview impact on false positives and false negatives dynamically via `/api/metrics/threshold` and `/metrics` page.

### 4.4 SHAP TreeExplainer Rationale
- **Why SHAP?**: SHAP (SHapley Additive exPlanations) is rooted in cooperative game theory, ensuring equitable attribution of each feature's contribution to moving a prediction away from the base expected value.
- **TreeExplainer Efficiency**: Unlike `KernelExplainer` (which samples predictions and takes seconds per transaction), `TreeExplainer` leverages tree structure paths to compute exact Shapley values in **< 5 milliseconds**.
- **Caching**: `ml/scorer.py` wraps model loading and SHAP explainer initialization in `@lru_cache`, ensuring zero disk re-reading during API scoring requests.

---

## 5. LLM Agent & Decision Support Flow

### 5.1 LangGraph 4-Node Orchestration
Case summaries are generated using a 4-node directed graph built with `langgraph`:

```mermaid
graph TD
    A[Node 1: load_history] --> B[Node 2: build_evidence]
    B --> C[Node 3: generate_summary]
    C --> D[Node 4: finalize]
```

1. **`load_history`**: Queries past transactions for the same customer to calculate historical chargeback history and average order value.
2. **`build_evidence`**: Combines current transaction attributes, customer profile stats, and top 3 positive/negative SHAP feature drivers into a structured context bundle.
3. **`generate_summary`**: Calls Ollama API (Llama 3.1 or Qwen2.5) with a zero-shot prompt requesting a concise 3-bullet breakdown: Key Risk Drivers, Historical Context, and Analyst Recommendation.
4. **`finalize`**: Formats output string and updates state graph.

### 5.2 Resilient Fallback Architecture
- **8-Second Timeout Constraint**: Calling local or remote LLMs can fail or lag due to hardware constraints. The agent wraps the LLM HTTP invocation in an 8-second timeout handler.
- **Deterministic Fallback Generator**: If Ollama is unavailable, uninstalled, or times out, `case_agent.py` automatically constructs a structured rule-based summary using top SHAP feature names and values. The user interface displays this gracefully labeled as `[Auto-generated summary]`, ensuring **100% uptime and zero reviewer blocking**.

---

## 6. Frontend Architecture & UX Engineering

### 6.1 Tech Stack & Code-Splitting
- **Framework**: React 18 with TypeScript and Vite for sub-second hot-module replacement (HMR).
- **Routing**: `react-router-dom` v6 with dynamic component lazy loading (`React.lazy` + `<Suspense>` wrapper). Page bundles (`DashboardPage`, `CaseDetailPage`, `MetricsPage`, `AuditPage`, `HelpPage`) are loaded on-demand, reducing initial bundle transfer size.

### 6.2 Tailwind v4 Design System & Visual Aesthetics
- **Tailwind v4 Setup**: Uses `@import "tailwindcss";` directive in `frontend/src/index.css`. Custom component styles and design tokens are declared using `@layer utilities` to maintain standard CSS specification compliance.
- **Theme**: Premium dark-mode palette (`slate-950` background, `slate-900/80` glassmorphism card containers, `emerald-500` low risk accents, `amber-500` medium risk accents, and `rose-500` high risk accents).

### 6.3 Custom SVG Gauge & Visualizations
- **`RiskGauge.tsx`**: Renders a dynamic semicircle vector gauge using standard SVG path arcs (`strokeDasharray` & `strokeDashoffset` calculations), eliminating reliance on heavy external charting library wrappers for simple gauges.
- **`ShapChart.tsx`**: Custom horizontal bar chart visualizing feature impacts. Positive risk factors render in red (`bg-rose-500`), while negative risk factors render in green (`bg-emerald-500`).

---

## 7. Database Schema & Data Lifecycle

The database follows a normalized relational structure (`backend/app/db/models.py`):

```mermaid
erDiagram
    CUSTOMERS ||--o{ TRANSACTIONS : places
    TRANSACTIONS ||--o| DECISIONS : receives
    USERS ||--o{ DECISIONS : submits
    USERS ||--o{ AUDIT_LOGS : generates

    CUSTOMERS {
        string id PK
        string email
        string risk_segment
        datetime created_at
    }

    TRANSACTIONS {
        string id PK
        string customer_id FK
        float amount
        string currency
        string payment_method
        float risk_score
        string risk_level
        json shap_values
        datetime created_at
    }

    DECISIONS {
        string id PK
        string transaction_id FK
        string reviewer_id FK
        string action
        string notes
        datetime created_at
    }

    USERS {
        string id PK
        string email
        string hashed_password
        string role
        datetime created_at
    }

    AUDIT_LOGS {
        integer id PK
        string user_id FK
        string action
        json details
        datetime timestamp
    }
```

---

## 8. Comprehensive File & Directory Breakdown

```
assessment project/
├── backend/                  # FastAPI Backend Application
│   ├── app/
│   │   ├── agent/            # LangGraph LLM agent workflow
│   │   │   └── case_agent.py # 4-node state graph + 8s timeout fallback
│   │   ├── api/              # API Route Handlers
│   │   │   ├── auth.py       # JWT login endpoint + sliding rate limiter
│   │   │   ├── deps.py       # FastAPI Dependency Injection (DB session, current user)
│   │   │   ├── metrics.py    # Model performance metrics & live threshold endpoints
│   │   │   └── transactions.py # Scoring, simulation, case detail & decision routes
│   │   ├── core/             # Application Infrastructure
│   │   │   ├── config.py     # Pydantic Settings env loader
│   │   │   ├── monitoring.py # Prometheus metrics definitions
│   │   │   └── security.py   # JWT encoding/decoding + bcrypt hashing
│   │   ├── db/               # Database Layer
│   │   │   ├── models.py     # SQLAlchemy ORM models (User, Transaction, etc.)
│   │   │   ├── seed.py       # Seed script for demo accounts & synthetic cases
│   │   │   └── session.py    # SQLAlchemy engine & session factory
│   │   ├── ml/               # Machine Learning Subsystem
│   │   │   └── scorer.py     # Singleton XGBoost scoring engine + SHAP TreeExplainer
│   │   ├── schemas/          # Data Validation
│   │   │   └── schemas.py    # Pydantic request/response schemas
│   │   └── main.py           # FastAPI app entrypoint with lifespan startup tasks
│   └── tests/
│       └── test_api.py       # Pytest test suite (19 test cases)
├── frontend/                 # React 18 + TypeScript + Vite Frontend
│   ├── src/
│   │   ├── components/       # UI Components (RiskGauge, ShapChart, Sidebar, etc.)
│   │   ├── contexts/         # AuthContext provider (JWT state & login/logout)
│   │   ├── lib/              # Axios API client setup + helper utilities
│   │   ├── pages/            # View pages (Login, Dashboard, CaseDetail, Metrics, etc.)
│   │   ├── types/            # TypeScript interface definitions matching backend schemas
│   │   ├── App.tsx           # Router configuration & protected route wrappers
│   │   ├── index.css         # Tailwind v4 import & custom CSS utility layer
│   │   └── main.tsx          # React application root DOM mount
│   ├── package.json          # Node dependencies & script commands
│   └── vite.config.ts        # Vite config with backend proxy settings
├── artifacts/                # Trained ML artifacts (model.joblib, metrics.json, etc.)
├── data/                     # Raw synthetic dataset (synthetic_transactions.parquet)
├── scripts/                  # Data generation & training execution scripts
│   ├── generate_data.py      # Synthetic financial data generator
│   ├── train.py              # XGBoost training & threshold optimization
│   └── precompute_demo.py    # Pre-scoring script for demo UI cases
├── Dockerfile                # Production multi-stage Docker build specification
├── docker-compose.yml        # Docker Compose configuration (App + Postgres + Ollama)
├── requirements.txt          # Python dependencies (with pinned bcrypt==4.0.1)
└── README.md                 # Project Overview & Quickstart Guide
```

---
*FraudLens is an open-source, explainable AI demonstration platform designed for evaluation and operational decision support.*
