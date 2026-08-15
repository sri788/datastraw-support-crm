# Enterprise Support CRM & AI Triage System

A full-stack, production-grade Customer Support Ticketing CRM built with Python FastAPI, SQLite, Jinja2, and Tailwind CSS. Built for the Datastraw Technologies Engineering Assessment.

## 🚀 Live Demo & Documentation
- **Live Application URL:** [https://datastraw-support-crm.onrender.com](https://datastraw-support-crm.onrender.com)
- **Interactive REST API Docs (Swagger):** [https://datastraw-support-crm.onrender.com/docs](https://datastraw-support-crm.onrender.com/docs)

---

## ✨ Features
1. **Create Support Tickets:** Customer details, auto-generated unique `TKT-DS-XXXX` IDs, VIP customer detection (`@datastraw.com`), and initial `Open` status.
2. **Dashboard Analytics:** Live metrics tracking Total, Open, In Progress, and Closed tickets.
3. **Instant Search & Status Filtering:** Search-as-you-type across Customer Names, Emails, Subjects, and Ticket IDs with tabbed status filtering (`All`, `Open`, `In Progress`, `Closed`).
4. **Ticket Detail & Team Activity Feed:** Complete issue breakdown, status updates (`Open` -> `In Progress` -> `Closed`), and internal team activity notes.
5. **⭐ Stand-Out Feature - Natural Language AI Triage Engine:**
   - Evaluates ticket urgency and assigns SLA priorities (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
   - Recommends operational action plans and posts them directly into the team notes feed.

---

## 🛠️ Technology Stack
- **Backend API:** Python 3.11+, FastAPI, Uvicorn, Pydantic
- **Database:** SQLite (Relational schema: `tickets` and `notes` tables)
- **Frontend UI:** HTML5, Jinja2 Templates, Tailwind CSS (Dark Mode), FontAwesome
- **Deployment:** Render.com

---

## 🔌 REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/tickets` | Create a new ticket (Returns `ticket_id`, `created_at`) |
| `GET` | `/api/tickets` | List tickets (Supports `?status=Open` & `?search=query`) |
| `GET` | `/api/tickets/{id}` | Get ticket details + attached team notes |
| `PUT` | `/api/tickets/{id}` | Update ticket status or post internal note |
| `POST` | `/api/tickets/{id}/ai-triage` | Trigger AI Triage analysis and post diagnostic note |

---

## 💻 Local Setup Instructions

```bash
# 1. Clone repository
git clone https://github.com/sri788/datastraw-support-crm.git
cd datastraw-support-crm

# 2. Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start local Uvicorn server
uvicorn app.main:app --reload
