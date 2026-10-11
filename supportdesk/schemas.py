from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models import TeamRole, TicketPriority, TicketStatus, UserRole


class UserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255, examples=["priya.nair@example.com"])
    full_name: str = Field(min_length=1, max_length=100, examples=["Priya Nair"])
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["Cannot reset my password"])
    description: str = Field(min_length=1, examples=["The reset email never arrives."])
    priority: TicketPriority = TicketPriority.NORMAL


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, examples=["Could you tell us which email address you reset it for?"])


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author_id: int
    body: str
    created_at: datetime


class TicketUpdate(BaseModel):
    title: str = Field(default=None, min_length=1, max_length=200)
    description: str = Field(default=None, min_length=1)
    status: TicketStatus = None
    priority: TicketPriority = None
    assignee_id: int | None = None


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    customer_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime


class TicketPage(BaseModel):
    items: list[TicketRead]
    total: int
    limit: int
    offset: int


class TicketDetail(TicketRead):
    customer: UserRead
    assignee: UserRead | None
    comments: list[CommentRead]


class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100, examples=["Billing support"])


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MembershipCreate(BaseModel):
    user_id: int
    role: TeamRole = TeamRole.MEMBER


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserRead
    role: TeamRole
    joined_at: datetime


class TeamDetail(TeamRead):
    memberships: list[MemberRead]
