# NovaWorks AI Project Management CRM
**The Infinity Hack ’26 — AI Project Manager: Meeting to Execution**  
*Company: NovaWorks Technologies, Lahore, Pakistan*

---

## 📌 Project Overview
NovaWorks CRM is an intelligent project management platform tailored for software agencies. Instead of project managers spending hours transcribing meeting notes into task backlogs, the CRM allows administrators to paste a planning meeting transcript. An AI engine parses the discussion, extracts client projects and work items, maps them to existing team members according to role and specialization, accounts for final agreed revisions, and excludes rejected features—instantly creating a structured deliverable roadmap with strict Role-Based Access Control (RBAC).

---

## 🚀 Key Features

1. **Role-Based Access Control (RBAC) & Data Isolation**:
   - **Administrator (`ADMIN`)**: Complete visibility over all projects and tasks. Exclusive permission to convert transcripts into projects and tasks, and manage workspace data.
   - **Project Manager (`MANAGER`)**: Filtered strictly to their assigned projects (`managerId == currentUser.id`) and all tasks inside those projects. Direct access to other projects is strictly rejected (403).
   - **Developer Agent (`AGENT`)**: Sees distinct projects containing their assigned tasks and **only their assigned tasks** in those projects. Other agents' tasks are strictly hidden at the API level.
2. **AI Transcript-to-Project Automation (Dual-Engine)**:
   - **Dual-Engine Architecture**: Supports live Google Gemini (`gemini-2.0-flash` / `gemini-1.5-pro`) and OpenAI (`gpt-4o-mini`) via `.env` configuration, backed by a built-in high-precision **Semantic NLP Parser** that works 100% offline with zero external API keys!
   - **Dispute Resolution & Revisions**: Properly applies final agreements over initial rough estimates (e.g., UrbanCart deadline 20 Oct vs 18 Oct; UrbanCart integration 19 Oct vs 17 Oct; QuickServe integration 10 hrs vs 8 hrs; Maryam owning HelpDeskPro evaluation instead of Zain).
   - **Negative Scope Filtering**: Excludes explicitly rejected features (payment gateways, stock/inventory integration, live driver maps, external ticketing/email).
   - **Strict Entity Guardrails**: Rejects non-company personnel (e.g. Kamran is not a NovaWorks employee and is never assigned tasks or created as a user).
3. **Atomic Database Transactions**:
   - All-or-nothing transactional save: if any task date exceeds a project deadline or references an invalid user, the database rolls back completely to prevent orphan records.
4. **Interactive Single-Page Application (SPA)**:
   - Clean, modern, responsive UI with project cards, task breakdowns, a read-only team directory, toast alerts, loading indicators, and an instant **1-Click Demo Account Switcher** to test all 10 user roles effortlessly.
5. **Zero External Dependencies**:
   - Built entirely on the Python 3 standard library (`http.server`, `sqlite3`, `hashlib`, `json`, `re`, `pathlib`). Runs cleanly on any machine with Python 3.9+ without needing `pip install`!

---

## 👥 Demo User Accounts

All demo accounts come pre-configured with the standard demo password: `Demo123!`

| Reference | Name | Demo Email | Role | Specialization | Skills |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ADMIN** | Admin | `admin@novaworks.example` | `ADMIN` | Administrator | Company overview, transcript creation |
| **PM01** | Ayesha Khan | `ayesha@novaworks.example` | `MANAGER` | Manager / Web PM | Web projects, client coordination |
| **PM02** | Bilal Ahmed | `bilal@novaworks.example` | `MANAGER` | Manager / Mobile PM | Mobile projects, delivery planning |
| **PM03** | Hina Malik | `hina@novaworks.example` | `MANAGER` | Manager / AI PM | AI projects, requirement review |
| **DEV01** | Ali Raza | `ali@novaworks.example` | `AGENT` | Agent / Full-Stack | React, frontend integration |
| **DEV02** | Hamza Shah | `hamza@novaworks.example` | `AGENT` | Agent / Full-Stack | Node.js, databases, APIs |
| **DEV03** | Sara Noor | `sara@novaworks.example` | `AGENT` | Agent / App Developer | Flutter, mobile UI |
| **DEV04** | Usman Tariq | `usman@novaworks.example` | `AGENT` | Agent / App Developer | Flutter, integration, testing |
| **DEV05** | Zain Abbas | `zain@novaworks.example` | `AGENT` | Agent / AI Developer | LLMs, extraction, prompts |
| **DEV06** | Maryam Asif | `maryam@novaworks.example` | `AGENT` | Agent / AI Developer | Retrieval, document processing |

---

## 🛠️ Tech Stack & Architecture

- **Backend**: Python 3 (`http.server.ThreadingHTTPServer` with REST routing and CORS support)
- **Database**: SQLite 3 with WAL mode, foreign keys (`PRAGMA foreign_keys = ON;`), and atomic transaction contexts
- **Security & Auth**: PBKDF2-HMAC-SHA256 password hashing (100,000 rounds), cryptographically secure session tokens, HTTP-only session cookies
- **AI Engine**: Dual-Engine (Google Gemini / OpenAI API + Deterministic Semantic NLP Extraction Engine)
- **Frontend**: Responsive Single-Page Application (HTML5, Vanilla CSS3 with Modern Variables, Vanilla ES6 JavaScript)
- **Testing**: Automated end-to-end Python test suite (`test_crm.py`, `test_modified.py`)

---

## ⚡ Quick Start & Run Commands

### 1. Prerequisites
- Python 3.9+ (Tested and verified on Python 3.14)
- No `pip install` required! (Zero external dependencies)

### 2. Setup Environment
```bash
# Clone the repository
git clone <repo-url>
cd novaworks-crm

# Optional: configure environment variables
cp .env.example .env
```

### 3. Initialize & Seed Demo Accounts
Run the idempotent seeder to setup the SQLite database and insert the 10 demo users:
```bash
python scripts/seed.py
```

### 4. Start the Application Server
```bash
python main.py
```
Open your browser at: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🧪 Automated Testing

A comprehensive automated test suite is provided to verify RBAC isolation, data integrity, AI extraction, and dynamic input handling.

```bash
# Run complete test suite (Database, Seeding, Authentication, RBAC, AI Extraction)
python scripts/test_crm.py

# Run test on modified transcript (QuickServe integration 12h, 23 Oct)
python scripts/test_modified.py
```

---

## 📋 Step-by-Step Demonstration Walkthrough

Follow these steps to evaluate the application against the challenge requirements:

1. **Initial State & Demo Seeder**:
   - Launch the application and observe the Login screen.
   - Notice the **1-Click Quick Demo Switcher** grid containing all 10 demo accounts.
2. **Admin Login & Transcript Automation**:
   - Log in as **Admin** (`admin@novaworks.example` / `Demo123!`).
   - Click **"Create from Transcript"** in the topbar or sidebar.
   - Click **"📋 Load Standard 60-min Transcript"** (or paste your own meeting notes).
   - Click **"Process & Generate Projects"**.
   - The AI extracts and saves **3 Projects** and **12 Tasks** atomically into the database.
3. **Verify Projects & Tasks**:
   - **UrbanCart Website** (Client: UrbanCart Clothing, Manager: Ayesha Khan, Deadline: `2026-10-20`):
     - Product catalog UI (Ali, 12h, `2026-10-12`)
     - Demo cart UI (Ali, 8h, `2026-10-15`)
     - Product and cart APIs (Hamza, 14h, `2026-10-14`)
     - Website integration and testing (Ali, 6h, `2026-10-19` — *revised date verified!*)
   - **QuickServe Mobile App** (Client: QuickServe Services, Manager: Bilal Ahmed, Deadline: `2026-10-24`):
     - Login and profile screens (Sara, 8h, `2026-10-12`)
     - Service booking screens (Sara, 12h, `2026-10-17`)
     - Booking and account APIs (Hamza, 16h, `2026-10-16`)
     - Mobile integration and testing (Usman, 10h, `2026-10-22` — *revised 10h verified!*)
   - **HelpDeskPro AI Assistant** (Client: HelpDeskPro Solutions, Manager: Hina Malik, Deadline: `2026-10-22`):
     - FAQ document processing (Maryam, 10h, `2026-10-13`)
     - Assistant answer generation (Zain, 14h, `2026-10-17`)
     - Human escalation flow (Zain, 6h, `2026-10-18`)
     - Assistant evaluation and testing (Maryam, 8h, `2026-10-21` — *revised owner Maryam verified!*)
   - Excluded tasks: payments, inventory, maps, driver tracking, external emails are **not present**.
   - Kamran is **not in the team directory** and has no tasks assigned.
4. **Test Role-Based Access Isolation**:
   - Switch to **Ayesha Khan (Manager)**:
     - Only **UrbanCart Website** is visible.
     - Projects managed by Bilal or Hina cannot be accessed or viewed.
   - Switch to **Ali Raza (Agent)**:
     - Sees only **UrbanCart Website** (the project containing his assigned work).
     - Under UrbanCart task details, Ali sees **only his 3 assigned tasks**. Hamza's task is strictly hidden.
   - Switch to **Hamza Shah (Agent)**:
     - Sees **2 Projects** (UrbanCart Website and QuickServe Mobile App).
     - Under each project, Hamza sees **only his 2 assigned API tasks**.
5. **Persistence Check**:
   - Refresh the page or restart the server with `python main.py`. All projects and tasks remain saved in `novaworks.db`.
6. **Dynamic AI Conversion (Modified Input Test)**:
   - Switch to Admin, click **"Reset Demo"** or open **"Create from Transcript"**.
   - Click **"⚡ Load Modified Transcript (QuickServe 12h / 23 Oct)"**.
   - Process with AI and verify that QuickServe's Mobile integration task dynamically updates to **12 hours** and deadline **`2026-10-23`**, proving dynamic processing rather than a static template.

---

## 🌐 Deployment Guide

### Deployment Options:
1. **Hosted Container / Virtual Machine (Render / Railway / DigitalOcean / AWS EC2)**:
   - Command: `python main.py`
   - Port: Set `PORT` environment variable (e.g. `PORT=8080`).
   - SQLite database persists on a persistent volume mount, or connect to hosted PostgreSQL using an adapter.
2. **Hosted PostgreSQL (Aiven Free PostgreSQL)**:
   - Aiven PostgreSQL connection URL can be passed in `DATABASE_URL`. The schema is ANSI SQL compliant and runs seamlessly on both SQLite and PostgreSQL.

---

## 📄 License & Evaluation Note
Submitted for **THE INFINITY HACK ’26 | AI Project Manager Challenge**.  
All fictional employee names, client names, and transcripts are part of the challenge specification.
