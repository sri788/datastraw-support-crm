import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Request, status as st
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator

from app.database import get_conn, init_db, get_tkt_id

app = FastAPI(title="Datastraw Support CRM")

# Setup template & static directories
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(base_dir, "static")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

tmpl = Jinja2Templates(directory=os.path.join(base_dir, "templates"))

@app.on_event("startup")
def startup():
    init_db()

class CRMError(Exception):
    def __init__(self, msg: str, code: int = 400):
        self.msg = msg
        self.code = code

@app.exception_handler(CRMError)
def err_handler(req: Request, exc: CRMError):
    return JSONResponse(status_code=exc.code, content={"error": exc.msg})

# DTOs
class CreateDTO(BaseModel):
    customer_name: str
    customer_email: str
    subject: str
    description: str

    @field_validator('customer_name', 'subject', 'description')
    @classmethod
    def check_str(cls, v: str) -> str:
        return v.strip() if (v and v.strip()) else ValueError("Invalid input")

    @field_validator('customer_email')
    @classmethod
    def check_email(cls, v: str) -> str:
        return v.strip().lower() if ("@" in v and "." in v.split("@")[-1]) else ValueError("Invalid email")

class UpdateDTO(BaseModel):
    status: Optional[str] = None
    note_text: Optional[str] = None

# Views
@app.get("/")
def home(request: Request):
    return tmpl.TemplateResponse(request=request, name="index.html")

@app.get("/ticket/{ticket_id}")
def detail(request: Request, ticket_id: str):
    return tmpl.TemplateResponse(request=request, name="detail.html", context={"ticket_id": ticket_id})

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")

# Endpoints
@app.post("/api/tickets", status_code=st.HTTP_201_CREATED)
def add_ticket(dto: CreateDTO):
    conn = get_conn()
    cur = conn.cursor()

    tid = get_tkt_id()
    curr_time = datetime.now(timezone.utc).isoformat()
    # flag enterprise email domains as VIP
    vip = 1 if dto.customer_email.endswith(("@datastraw.in", "@enterprise.com")) else 0

    try:
        cur.execute("""
            INSERT INTO tickets (ticket_id, customer_name, customer_email, subject, description, status, is_vip, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'Open', ?, ?, ?);
        """, (tid, dto.customer_name, dto.customer_email, dto.subject, dto.description, vip, curr_time, curr_time))
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise CRMError(f"Error creating ticket: {str(e)}", code=500)

    conn.close()
    return {"ticket_id": tid, "created_at": curr_time, "status": "Open", "is_vip": bool(vip)}

@app.get("/api/tickets")
def get_tickets(status: Optional[str] = None, search: Optional[str] = None):
    conn = get_conn()
    cur = conn.cursor()

    q = "SELECT * FROM tickets WHERE 1=1"
    args = []

    if status and status.lower() != "all":
        q += " AND LOWER(status) = LOWER(?)"
        args.append(status)

    if search:
        s = f"%{search.strip()}%"
        # search across multiple fields
        q += " AND (customer_name LIKE ? OR customer_email LIKE ? OR subject LIKE ? OR ticket_id LIKE ?)"
        args.extend([s, s, s, s])

    # float VIP tickets to top
    q += " ORDER BY is_vip DESC, id DESC"

    cur.execute(q, args)
    res = [dict(r) for r in cur.fetchall()]
    conn.close()
    return res

@app.get("/api/tickets/{ticket_id}")
def get_ticket_by_id(ticket_id: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE ticket_id = ?;", (ticket_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise CRMError(f"Ticket {ticket_id} not found", code=404)

    tkt = dict(row)
    # fetch attached notes feed
    cur.execute("SELECT * FROM notes WHERE ticket_id = ? ORDER BY id DESC;", (ticket_id,))
    tkt["notes"] = [dict(n) for n in cur.fetchall()]

    conn.close()
    return tkt

@app.put("/api/tickets/{ticket_id}")
def update_ticket(ticket_id: str, dto: UpdateDTO):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM tickets WHERE ticket_id = ?;", (ticket_id,))
    if not cur.fetchone():
        conn.close()
        raise CRMError(f"Ticket {ticket_id} not found", code=404)

    curr_time = datetime.now(timezone.utc).isoformat()

    if dto.status:
        st_list = ["Open", "In Progress", "Closed"]
        if dto.status not in st_list:
            conn.close()
            raise CRMError("Invalid status")
        cur.execute("UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?;", (dto.status, curr_time, ticket_id))

    if dto.note_text and dto.note_text.strip():
        cur.execute("INSERT INTO notes (ticket_id, note_text, created_at) VALUES (?, ?, ?);",
                    (ticket_id, dto.note_text.strip(), curr_time))

    conn.commit()
    conn.close()
    return {"success": True, "updated_at": curr_time}

# AI triage feature
@app.post("/api/tickets/{ticket_id}/ai-triage")
def ai_triage(ticket_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tickets WHERE ticket_id = ?;", (ticket_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise CRMError("Ticket not found", code=404)

    tkt = dict(row)
    txt = (tkt['subject'] + " " + tkt['description']).lower()
    sub = tkt['subject'].strip()

    # triage rule matching
    if any(k in txt for k in ["cashier", "billing", "payment", "fraud", "hacked", "money"]):
        prio, sla = "CRITICAL", "1 Hour SLA"
        act = f"Financial alert on '{sub}'. Escalated to Operations Lead."
    elif any(k in txt for k in ["down", "crash", "outage", "500", "database", "server"]):
        prio, sla = "HIGH", "4 Hour SLA"
        act = f"System error on '{sub}'. Route to Infrastructure team."
    elif any(k in txt for k in ["remote", "tv", "lost", "hardware"]):
        prio, sla = "LOW", "48 Hour SLA"
        act = f"Hardware replacement request for '{sub}'. Order dispatched."
    else:
        prio, sla = "MEDIUM", "24 Hour SLA"
        act = f"General inquiry regarding '{sub}'. Assigned to Support."

    vip_str = " [VIP Account]" if tkt.get("is_vip") else ""
    summary = f"🤖 [Datastraw Triage Engine]: Priority = {prio} ({sla}){vip_str}. Action: {act}"

    curr_time = datetime.now(timezone.utc).isoformat()
    cur.execute("INSERT INTO notes (ticket_id, note_text, created_at) VALUES (?, ?, ?);", (ticket_id, summary, curr_time))
    conn.commit()
    conn.close()

    return {"success": True, "ai_summary": summary}