# Stocker: Autonomous Multi-Store Supply Chain & Inventory Optimization Platform

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.2-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4.0-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Facebook Prophet](https://img.shields.io/badge/Prophet-1.1-1877F2?logo=facebook&logoColor=white)](https://facebook.github.io/prophet/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)

An enterprise-grade, autonomous supply chain and multi-store inventory intelligence platform. **Stocker** combines machine learning demand forecasting, operations research mathematical optimization, inter-store rebalancing transfers, lead-time aware procurement, and a multilingual AI Copilot to eliminate stockouts and reduce inventory carrying costs across retail networks.

---

## 📋 Table of Contents

- [Core Architectural Pillars](#-core-architectural-pillars)
- [Key Features](#-key-features)
- [Multilingual AI Copilot](#-multilingual-ai-copilot)
- [Project Architecture & Directory Structure](#-project-architecture--directory-structure)
- [Quick Start Guide](#-quick-start-guide)
- [Database Seeding (10,000 Records)](#-database-seeding-10000-records)
- [Demo Credentials & Role-Based Access](#-demo-credentials--role-based-access)
- [Tech Stack](#-tech-stack)
- [API Documentation](#-api-documentation)
- [Environment Variables](#-environment-variables)
- [License](#-license)

---

## 🏛️ Core Architectural Pillars

Stocker is built upon **4 foundational pillars of modern supply chain engineering**:

```
                       ┌─────────────────────────────────────────────────────────────┐
                       │                     STOCKER PLATFORM                        │
                       └──────┬───────────────┬───────────────┬───────────────┬──────┘
                              │               │               │               │
                              ▼               ▼               ▼               ▼
                       ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
                       │  PILLAR 1   │ │  PILLAR 2   │ │  PILLAR 3   │ │  PILLAR 4   │
                       │   Demand    │ │ Inter-Store │ │ Lead-Time   │ │   Cost      │
                       │ Forecasting │ │ Rebalancing │ │ Procurement │ │Optimization │
                       │  (Prophet + │ │  (Surplus   │ │  (Order-By  │ │ (Dynamic    │
                       │  Croston)   │ │  Balancing) │ │ Directives) │ │  EOQ + ROP) │
                       └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### 1. Dual-Engine Demand Forecasting (Prophet & Croston ML)
- **Continuous Demand**: Uses **Facebook Prophet** with weekly/yearly seasonality and automated holiday regressors to generate 30- to 365-day confidence-interval forecasts.
- **Intermittent & Erratic Spare Parts**: Utilizes **Croston's Method** to decompose intermittent auto parts sales into demand size and inter-arrival intervals, avoiding zero-demand bias.
- **Accuracy Telemetry**: Continuous tracking of Mean Absolute Percentage Error (MAPE).

### 2. Autonomous Inter-Store Inventory Balancing
- Identifies stores facing impending stockouts and pairs them with neighboring stores carrying surplus inventory.
- Generates proactive **store-to-store transfer directives** to satisfy customer demand immediately with zero vendor purchase orders and minimal transfer logistics costs.

### 3. Lead-Time Aware Procurement & "Order-By" Directives
- Calculates vendor procurement deadlines backwards from supplier lead times (e.g., 7d, 14d, 21d).
- Determines the exact date by which purchase orders must be dispatched so replacement stock lands at the warehouse before safety stock is breached.

### 4. Operations Research Cost Optimization (Dynamic EOQ + ROP)
- Minimizes the total cost curve (Holding Cost vs. Ordering Cost) via the Economic Order Quantity theorem:
  $$\text{EOQ} = \sqrt{\frac{2DS}{H}}$$
  *(where $D$ = Annual Demand, $S$ = Setup/Ordering Cost, $H$ = Annual Unit Holding Cost)*
- Dynamically adapts Reorder Points (ROP) factoring in demand volatility during lead times:
  $$\text{ROP} = (d \times L) + Z \times \sigma_L$$
  *(where $d$ = Daily Demand, $L$ = Supplier Lead Time, $Z$ = Service Level Factor, $\sigma_L$ = Standard Deviation of Lead-Time Demand)*

---

## ⚡ Key Features

- **Executive Command Center**: Live KPIs including inventory turnover ratio, network-wide forecast MAPE, demand risk score, category mix, and real-time revenue velocity.
- **K-Means Cluster Analysis**: Automated optimal cluster discovery via the Elbow Method (inertia minimization) to categorize store-SKU velocity cohorts.
- **Automated Anomaly Detection**: Statistical Z-Score and Exponentially Weighted Moving Average (EWMA) tracking to flag demand surges, sudden drops, and anomalous ordering behavior.
- **Role-Based Access Control (RBAC)**: Fine-grained permissions across 4 defined enterprise roles (`admin`, `operations`, `analyst`, `executive`).
- **Fleet Design System**: Modern Fleet & Autonomous SCM design theme with brushed metallic silver and titanium accents, tactile glassmorphism panels, and a cinematic logo splash intro transition.

---

## 🤖 Multilingual AI Copilot

Stocker includes an integrated real-time **AI Supply Chain Copilot**:

- **Real-Time Database RAG**: Ingests live database tables (`stocker_demo.db` / PostgreSQL) to answer questions about low stock SKUs, recommended transfers, lead-time deadlines, and EOQ math.
- **Universal Multilingual Support**: Fully understands and replies in the user's input language, including **English, हिन्दी (Hindi), मराठी (Marathi), Hinglish, Spanish, French**, and more.
- **Google Gemini & Local Intelligence**: Native Google Gemini API support (configure custom keys directly in the chat drawer) with seamless zero-dependency offline fallback.
- **Sleek Single Launcher**: Accessible via a clean top-bar trigger and global keyboard shortcut:
  - <kbd>⌘J</kbd> (Mac) or <kbd>Ctrl+J</kbd> (Windows/Linux) to toggle from any page.
  - <kbd>Esc</kbd> to dismiss.

---

## 🗂️ Project Architecture & Directory Structure

```
Stocker/
├── backend/                       # Python Flask API & Machine Learning Engine
│   ├── routes/                    # Modular Blueprint Endpoints
│   │   ├── analytics.py           # Dashboard KPIs, clusters, turnover, revenue trends
│   │   ├── anomalies.py           # Anomaly detection & resolution workflows
│   │   ├── auth.py                # JWT authentication & user profile management
│   │   ├── chat.py                # AI Copilot chatbot endpoints (RAG & Gemini)
│   │   ├── forecast.py            # Prophet & Croston ML forecasting routes
│   │   ├── inventory.py           # Multi-store stock positions & EOQ/ROP optimization
│   │   └── recommendations.py    # AI transfers & procurement directives
│   ├── services/                  # Business Logic & Algorithms
│   │   ├── chat_service.py        # Multilingual Copilot & semantic RAG engine
│   │   └── forecast_service.py    # Facebook Prophet & Croston ML implementation
│   ├── scripts/                   # Migration & Bulk Data Tools
│   │   ├── seed_bulk_data.py      # 10,000-record synthetic seed generator
│   │   └── init_db.py             # Database table initialization
│   ├── database/                  # SQLAlchemy ORM Models & Session Management
│   ├── tests/                     # Pytest Unit & Integration Suite
│   ├── server.py                  # Flask Application Factory & Middleware
│   ├── requirements.txt           # Python backend dependencies
│   └── README.md                  # Backend API documentation
│
├── frontend/                      # React 19 + TypeScript + Vite Single-Page App
│   ├── src/
│   │   ├── components/            # Reusable UI & Layout Components
│   │   │   ├── chat/              # Chatbot drawer, Markdown renderer, launcher
│   │   │   ├── layout/            # AppShell, Navbar, Sidebar, ProtectedRoute
│   │   │   └── ui/                # Tactile cards, badges, logo, splash transition
│   │   ├── contexts/              # AuthContext (JWT) & ThemeContext (Dark/Light)
│   │   ├── lib/                   # Chart theme tokens, roles, and helper utilities
│   │   ├── pages/                 # Route Views
│   │   │   ├── DashboardPage.tsx  # Executive Command Center
│   │   │   ├── ForecastPage.tsx   # Prophet & Croston Time-Series Visualizer
│   │   │   ├── InventoryPage.tsx  # EOQ/ROP Grid & Inter-Store Rebalancing
│   │   │   ├── AnalyticsPage.tsx  # K-Means Clustering & Velocity Matrix
│   │   │   ├── AnomaliesPage.tsx  # EWMA Anomaly Feed & Resolution
│   │   │   ├── RecommendationsPage.tsx # AI Transfer & Order-By Directives
│   │   │   ├── LoginPage.tsx      # Secure Authentication Screen
│   │   │   ├── ReportsPage.tsx    # Operational Summary Export
│   │   │   └── SettingsPage.tsx   # Enterprise Preferences
│   │   ├── services/api.ts        # Axios API Client & Type Definitions
│   │   ├── App.tsx                # Client Routing & Guard Orchestration
│   │   ├── main.tsx               # React Entrypoint
│   │   └── index.css              # Fleet design tokens, silver & titanium accents
│   ├── package.json               # Node.js dependencies
│   ├── vite.config.ts             # Vite build configuration
│   └── tsconfig.json              # TypeScript strict configuration
│
├── .env.example                   # Environment configuration template
└── README.md                      # Project documentation (this file)
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: 3.10 or 3.11
- **Node.js**: v18 or later (npm v9+)

### 1. Clone the Repository
```bash
git clone https://github.com/swarajgurme/Stocker.git
cd Stocker
```

### 2. Backend Setup & Startup
```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Run server with demo database (runs on port 5001 to avoid macOS AirPlay conflict)
SKIP_ALEMBIC=true DATABASE_URL=sqlite:///stocker_demo.db FLASK_PORT=5001 python server.py
```
> The backend API will be live at `http://127.0.0.1:5001`. Verify via `http://127.0.0.1:5001/health`.

### 3. Frontend Setup & Startup
In a separate terminal:
```bash
cd frontend

# Install Node dependencies
npm install

# Start development server
npm run dev -- --port 5173
```
> The frontend application will be live at `http://localhost:5173`.

---

## 🌱 Database Seeding (10,000 Records)

Stocker includes a high-performance synthetic bulk data generator that builds realistic demand distributions across 5 store nodes and 20 automotive parts:

```bash
cd backend
source venv/bin/activate

# Seed 10,000 realistic sales rows, inventory levels, forecasts, anomalies, and demo users:
python scripts/seed_bulk_data.py --replace --count 10000
```

### Seeding CLI Parameters
| Flag | Default | Description |
|------|---------|-------------|
| `--count N` | `10000` | Target historical sales transactions to generate |
| `--replace` | `False` | Cleanly resets transactional tables before seeding |
| `--seed N` | `42` | Random number generator seed for reproducible trends |
| `--demo-password` | `DemoPass123!` | Master password assigned to all seeded demo users |
| `--span-days N` | `730` | Time horizon (in days) spanning past historical data |

---

## 👥 Demo Credentials & Role-Based Access

The seeded dataset provides pre-configured role-based test accounts:

| Email | Role | Accessible Views | Default Password |
|---|---|---|---|
| `admin@stocker.demo` | **Administrator** | Full platform access + settings & user controls | `DemoPass123!` |
| `exec@stocker.demo` | **Executive** | Executive Dashboard, KPIs, Revenue, Reports | `DemoPass123!` |
| `manager@stocker.demo` | **Operations Manager** | Forecasting, Inventory, AI Recommendations | `DemoPass123!` |
| `analyst@stocker.demo` | **Inventory Analyst** | Analytics, K-Means Clustering, Anomalies | `DemoPass123!` |
| `planner@stocker.demo` | **Demand Planner** | Forecasting, Inventory, Recommendations | `DemoPass123!` |

---

## 🛠️ Tech Stack

### Backend & Machine Learning
- **Python 3.11** & **Flask 3.0** (Application Factory, Blueprints)
- **SQLAlchemy 2.0** ORM (SQLite & PostgreSQL compatible)
- **Facebook Prophet 1.1** (Bayesian additive time series forecasting)
- **scikit-learn 1.3** (K-Means clustering & elbow method inertia calculation)
- **pandas 2.1** & **NumPy 1.24** (Time series aggregation & moving averages)
- **PyJWT 2.8** & **Passlib / Bcrypt** (Secure token authentication & password hashing)

### Frontend & Data Visualization
- **React 19** (Concurrent mode & modern hooks)
- **TypeScript 5.x** (Strict end-to-end type safety)
- **Vite 6** (Instant HMR & optimized production bundling)
- **Tailwind CSS 4.0** (Tactile Industrial Fleet design tokens)
- **Recharts** (Interactive time-series, area charts, category bars)
- **Framer Motion 12** (Smooth page transitions, layout animations & splash intro)
- **Lucide Icons** (Clean operational iconography)

---

## 📡 API Documentation

### Core Endpoints

| Category | Method | Endpoint | Description |
|---|---|---|---|
| **System** | `GET` | `/health` | Service status, database connectivity & version |
| **Auth** | `POST` | `/api/auth/login` | Authenticate user & issue JWT access/refresh tokens |
| **Auth** | `GET` | `/api/auth/me` | Fetch authenticated user profile & role |
| **Forecasting** | `POST` | `/api/forecast` | Run Prophet/Croston model for a specific Store + SKU |
| **Inventory** | `GET` | `/api/inventory` | Multi-store inventory levels, ROP thresholds & lead times |
| **Optimization** | `POST` | `/api/inventory/eoq` | Compute dynamic Economic Order Quantity & Reorder Points |
| **Analytics** | `GET` | `/api/analytics/dashboard` | Executive KPIs, turnover ratio, revenue velocity |
| **Analytics** | `GET` | `/api/analytics/clusters` | K-Means demand clustering analysis |
| **Anomalies** | `GET` | `/api/anomalies` | List statistical EWMA / Z-Score demand anomalies |
| **Directives** | `GET` | `/api/recommendations` | Proactive inter-store transfers & purchase order directives |
| **Copilot** | `POST` | `/api/chat` | Multilingual AI Copilot inference with live RAG context |
| **Copilot** | `GET` | `/api/chat/status` | Chat engine health, active provider, and database statistics |

---

## 🔧 Environment Variables

Configure `.env` in the project root or inside `backend/`:

```env
# Backend Environment Settings
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_PORT=5001
SECRET_KEY=stocker-enterprise-secret-key-change-in-production

# Database Configuration (SQLite default or PostgreSQL)
DATABASE_URL=sqlite:///stocker_demo.db
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/stocker_db
SKIP_ALEMBIC=true

# AI Copilot Optional Keys (or supply via frontend drawer)
GEMINI_API_KEY=your_gemini_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here

# Frontend Configuration
VITE_API_URL=http://127.0.0.1:5001
```

---

## 🧪 Testing

Stocker includes unit and integration test suites:

```bash
# Run backend tests
cd backend
PYTHONPATH=. pytest tests/ -v
```

```bash
# Verify frontend TypeScript build
cd frontend
npm run build
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
