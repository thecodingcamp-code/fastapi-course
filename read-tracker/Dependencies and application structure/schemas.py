from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

Status = Literal["to_read", "reading", "finished"]

Title = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    Field(description="The title of the book.", examples=["Deep Work"]),
]
Author = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    Field(description="The name of the author.", examples=["Cal Newport"]),
]
Pages = Annotated[int, Field(gt=0, le=5000, description="The number of pages.", examples=[304])]
Rating = Annotated[int, Field(ge=1, le=5, description="Your rating from 1 to 5 stars.", examples=[4])]
Tag = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=30),
]
Isbn = Annotated[
    str,
    Field(pattern=r"^\d{13}$", description="The 13-digit ISBN, digits only.", examples=["9781455586691"]),
]


class Publisher(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Avery"])
    year: int = Field(ge=1450, le=2100, examples=[2018])


class Note(BaseModel):
    page: Pages
    text: str = Field(min_length=1, max_length=500, description="What you want to remember.")


class BookBase(BaseModel):
    title: Title
    author: Author
    status: Status = Field(description="Where the book is in your reading list.")
    pages: Pages | None = None
    rating: Rating | None = None
    isbn: Isbn | None = None
    publisher: Publisher | None = None
    tags: list[Tag] = Field(default_factory=list, max_length=10, description="Up to 10 short labels.")
    notes: list[Note] = Field(default_factory=list, description="Notes tied to pages in the book.")


class BookCreate(BookBase):
    status: Status = Field(default="to_read", description="Where the book is in your reading list.")


class BookUpdate(BaseModel):
    title: Title | None = None
    author: Author | None = None
    status: Status | None = Field(default=None, description="A new status.")
    pages: Pages | None = None
    rating: Rating | None = None
    isbn: Isbn | None = None
    publisher: Publisher | None = None
    tags: list[Tag] | None = Field(default=None, max_length=10)


class BookRead(BookBase):
    id: int = Field(description="The unique id of the book.", examples=[2])


class BookRecord(BookRead):
    added_by: str
