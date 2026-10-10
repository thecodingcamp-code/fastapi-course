from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models import TicketPriority, TicketStatus, UserRole


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
