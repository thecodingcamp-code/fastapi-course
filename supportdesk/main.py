from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from database import DbSession
from models import Ticket, TicketPriority, TicketStatus, User, UserRole
from schemas import TicketCreate, TicketRead, TicketUpdate

app = FastAPI(
    title="SupportDesk API",
    description="Customers open support tickets, and agents work through them.",
    version="1.0.0",
)


MAX_ACTIVE_TICKETS = 5
ACTIVE_STATUSES = [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]


def count_active_tickets(db: Session, customer_id: int) -> int:
    query = select(func.count()).select_from(Ticket).where(
        Ticket.customer_id == customer_id,
        Ticket.status.in_(ACTIVE_STATUSES),
    )
    return db.scalar(query)


def open_ticket(db: Session, customer_id: int, data: TicketCreate) -> Ticket:
    ticket = Ticket(**data.model_dump(), customer_id=customer_id)
    db.add(ticket)
    if count_active_tickets(db, customer_id) > MAX_ACTIVE_TICKETS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A customer can have at most {MAX_ACTIVE_TICKETS} unresolved tickets",
        )
    return ticket


@app.get("/", summary="API status")
def read_root():
    """Check that the API is up."""
    return {"service": "SupportDesk API", "status": "running"}


@app.get("/health/db", summary="Database status")
def check_database(db: DbSession):
    """Run a trivial query to confirm the database answers."""
    version = db.execute(text("SELECT version()")).scalar_one()
    return {"database": "up", "server": version}


@app.get("/tickets", response_model=list[TicketRead], summary="List tickets")
def list_tickets(
    db: DbSession,
    ticket_status: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    assignee_id: int | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Return tickets ordered by id, optionally filtered."""
    query = select(Ticket)
    if ticket_status is not None:
        query = query.where(Ticket.status == ticket_status)
    if priority is not None:
        query = query.where(Ticket.priority == priority)
    if assignee_id is not None:
        query = query.where(Ticket.assignee_id == assignee_id)
    return db.scalars(query.order_by(Ticket.id).offset(skip).limit(limit)).all()


@app.get("/tickets/stats", summary="Ticket counts by status")
def ticket_stats(db: DbSession):
    """Count the tickets in each status."""
    rows = db.execute(select(Ticket.status, func.count()).group_by(Ticket.status)).all()
    counts = {s.value: 0 for s in TicketStatus}
    for ticket_status, total in rows:
        counts[ticket_status.value] = total
    return counts


def get_ticket(ticket_id: int, db: DbSession) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


FoundTicket = Annotated[Ticket, Depends(get_ticket)]


@app.get("/tickets/{ticket_id}", response_model=TicketRead, summary="Get one ticket")
def read_ticket(ticket: FoundTicket):
    """Return a single ticket, or 404 if it does not exist."""
    return ticket


@app.post("/tickets", response_model=TicketRead, status_code=status.HTTP_201_CREATED, summary="Open a ticket")
def create_ticket(payload: TicketCreate, customer_id: int, db: DbSession):
    """Open a ticket for the given customer."""
    if db.get(User, customer_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    ticket = open_ticket(db, customer_id, payload)
    db.commit()
    return ticket


@app.post("/tickets/bulk", response_model=list[TicketRead], status_code=status.HTTP_201_CREATED, summary="Open several tickets at once")
def create_tickets_bulk(payload: list[TicketCreate], customer_id: int, db: DbSession):
    """Open all the tickets in the request, or none of them."""
    if db.get(User, customer_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    tickets = [open_ticket(db, customer_id, item) for item in payload]
    db.commit()
    return tickets


@app.patch("/tickets/{ticket_id}", response_model=TicketRead, summary="Update a ticket")
def update_ticket(ticket: FoundTicket, changes: TicketUpdate, db: DbSession):
    """Change only the fields that the request sends."""
    values = changes.model_dump(exclude_unset=True)
    if values.get("assignee_id") is not None:
        agent = db.get(User, values["assignee_id"])
        if agent is None or agent.role != UserRole.AGENT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Assignee must be an existing agent",
            )
    for field, value in values.items():
        setattr(ticket, field, value)
    db.commit()
    return ticket


@app.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a ticket")
def delete_ticket(ticket: FoundTicket, db: DbSession):
    """Remove a ticket permanently."""
    db.delete(ticket)
    db.commit()
