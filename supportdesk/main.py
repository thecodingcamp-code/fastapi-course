import enum
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload, selectinload

from database import DbSession
from models import Comment, Team, TeamMembership, Ticket, TicketPriority, TicketStatus, User, UserRole
from schemas import (
    CommentCreate,
    CommentRead,
    MemberRead,
    MembershipCreate,
    TeamCreate,
    TeamDetail,
    TeamRead,
    TicketCreate,
    TicketDetail,
    TicketPage,
    TicketRead,
    TicketUpdate,
)

app = FastAPI(
    title="SupportDesk API",
    description="Customers open support tickets, and agents work through them.",
    version="1.0.0",
)


MAX_ACTIVE_TICKETS = 5
ACTIVE_STATUSES = [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]


class TicketSort(str, enum.Enum):
    NEWEST = "newest"
    OLDEST = "oldest"
    PRIORITY = "priority"


SORT_ORDER = {
    TicketSort.NEWEST: [Ticket.created_at.desc(), Ticket.id.desc()],
    TicketSort.OLDEST: [Ticket.created_at.asc(), Ticket.id.asc()],
    TicketSort.PRIORITY: [Ticket.priority.desc(), Ticket.created_at.desc(), Ticket.id.desc()],
}


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


@app.get("/tickets", response_model=TicketPage, summary="List tickets")
def list_tickets(
    db: DbSession,
    ticket_status: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    assignee_id: int | None = None,
    search: str | None = Query(default=None, min_length=2, max_length=100),
    sort: TicketSort = TicketSort.NEWEST,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Return one page of tickets, filtered and sorted."""
    filters = []
    if ticket_status is not None:
        filters.append(Ticket.status == ticket_status)
    if priority is not None:
        filters.append(Ticket.priority == priority)
    if assignee_id is not None:
        filters.append(Ticket.assignee_id == assignee_id)
    if search is not None:
        filters.append(Ticket.title.icontains(search, autoescape=True))

    total = db.scalar(select(func.count()).select_from(Ticket).where(*filters))
    items = db.scalars(
        select(Ticket).where(*filters).order_by(*SORT_ORDER[sort]).offset(offset).limit(limit)
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.get("/tickets/board", response_model=list[TicketDetail], summary="Tickets with people and comments")
def ticket_board(db: DbSession, limit: int = Query(default=20, ge=1, le=100)):
    """Return the newest tickets with their customers, assignees and comments."""
    query = (
        select(Ticket)
        .options(
            joinedload(Ticket.customer),
            joinedload(Ticket.assignee),
            selectinload(Ticket.comments),
        )
        .order_by(Ticket.id.desc())
        .limit(limit)
    )
    return db.scalars(query).all()


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


@app.get("/tickets/{ticket_id}", response_model=TicketDetail, summary="Get one ticket")
def read_ticket(ticket: FoundTicket):
    """Return a ticket with its customer, assignee and comments."""
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


@app.post(
    "/tickets/{ticket_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Comment on a ticket",
)
def add_comment(ticket: FoundTicket, payload: CommentCreate, author_id: int, db: DbSession):
    """Add a comment to a ticket, written by the given user."""
    author = db.get(User, author_id)
    if author is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")
    comment = Comment(body=payload.body, ticket=ticket, author=author)
    db.add(comment)
    db.commit()
    return comment


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


@app.post("/teams", response_model=TeamRead, status_code=status.HTTP_201_CREATED, summary="Create a team")
def create_team(payload: TeamCreate, db: DbSession):
    """Create a support team."""
    if db.scalar(select(Team).where(Team.name == payload.name)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A team with this name already exists")
    team = Team(name=payload.name)
    db.add(team)
    db.commit()
    return team


@app.get("/teams/{team_id}", response_model=TeamDetail, summary="Get a team with its members")
def read_team(team_id: int, db: DbSession):
    """Return a team and its memberships."""
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return team


@app.post(
    "/teams/{team_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to a team",
)
def add_member(team_id: int, payload: MembershipCreate, db: DbSession):
    """Add a user to a team, with a role."""
    team = db.get(Team, team_id)
    user = db.get(User, payload.user_id)
    if team is None or user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team or user not found")
    if db.get(TeamMembership, (team.id, user.id)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The user is already in this team")
    membership = TeamMembership(team=team, user=user, role=payload.role)
    db.add(membership)
    db.commit()
    return membership
