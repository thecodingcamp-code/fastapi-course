from typing import Annotated, Literal

from fastapi import Body, FastAPI, HTTPException, Path, Query
from pydantic import BaseModel, Field, StringConstraints

app = FastAPI(
    title="Reading Tracker API",
    description="""
Keep track of the books you are reading.

* Browse and filter your reading list
* Add, update, and remove books
* Every book has a status: `to_read`, `reading`, or `finished`
""",
    version="1.0.0",
    contact={"name": "Reading Tracker Support", "email": "support@readingtracker.example"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    openapi_tags=[
        {"name": "service", "description": "Basic information about the API itself."},
        {"name": "books", "description": "Create, read, update, and delete books in the reading list."},
        {"name": "notes", "description": "Notes attached to pages of a book."},
    ],
)

BOOKS = [
    {
        "id": 1, "title": "Atomic Habits", "author": "James Clear", "status": "finished",
        "pages": 320, "rating": 5, "isbn": "9780735211292", "added_by": "maya.chen@example.com",
        "publisher": {"name": "Avery", "year": 2018}, "tags": ["habits", "productivity"],
        "notes": [
            {"page": 27, "text": "Habits are the compound interest of self-improvement."},
            {"page": 144, "text": "Make the cue obvious, the craving attractive."},
        ],
    },
    {
        "id": 2, "title": "Deep Work", "author": "Cal Newport", "status": "reading",
        "pages": 304, "rating": None, "isbn": "9781455586691", "added_by": "maya.chen@example.com",
        "publisher": {"name": "Grand Central Publishing", "year": 2016}, "tags": ["focus", "productivity"],
        "notes": [
            {"page": 41, "text": "Depth is a skill, and it has to be trained."},
        ],
    },
    {
        "id": 3, "title": "The Pragmatic Programmer", "author": "David Thomas", "status": "to_read",
        "pages": 352, "rating": None, "isbn": "9780135957059", "added_by": "maya.chen@example.com",
        "publisher": {"name": "Addison-Wesley", "year": 2019}, "tags": ["programming", "craft"],
        "notes": [],
    },
    {
        "id": 4, "title": "Sapiens", "author": "Yuval Noah Harari", "status": "finished",
        "pages": 464, "rating": 4, "isbn": "9780062316097", "added_by": "maya.chen@example.com",
        "publisher": {"name": "Harper", "year": 2015}, "tags": ["history"],
        "notes": [],
    },
    {
        "id": 5, "title": "Project Hail Mary", "author": "Andy Weir", "status": "reading",
        "pages": 496, "rating": None, "isbn": "9780593135204", "added_by": "maya.chen@example.com",
        "publisher": {"name": "Ballantine Books", "year": 2021}, "tags": ["fiction", "science fiction"],
        "notes": [],
    },
]

Status = Literal["to_read", "reading", "finished"]

CURRENT_USER = "maya.chen@example.com"

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

BookId = Annotated[int, Path(gt=0, description="The id of the book.", examples=[2])]

NOT_FOUND = {404: {"description": "No book exists with this id."}}


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


def find_book(book_id: int):
    for book in BOOKS:
        if book["id"] == book_id:
            return book
    raise HTTPException(status_code=404, detail="Book not found")


@app.get("/", tags=["service"], summary="API status")
def read_root():
    """Check that the API is up and see which version is running."""
    return {
        "service": "Reading Tracker API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/books", response_model=list[BookRead], tags=["books"], summary="List books")
def list_books(
    status: Annotated[
        Status | None,
        Query(description="Only return books with this reading status."),
    ] = None,
    author: Annotated[
        str | None,
        Query(min_length=2, max_length=50, description="Only return books whose author contains this text, ignoring case."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="The maximum number of books to return.")] = 10,
):
    """Return the reading list, optionally filtered by status or author."""
    results = BOOKS
    if status is not None:
        results = [book for book in results if book["status"] == status]
    if author is not None:
        results = [book for book in results if author.lower() in book["author"].lower()]
    return results[:limit]


@app.get("/books/stats", tags=["books"], summary="Reading statistics")
def read_book_stats():
    """Count the books in the list, in total and for each reading status."""
    statuses = [book["status"] for book in BOOKS]
    return {
        "total": len(statuses),
        "to_read": statuses.count("to_read"),
        "reading": statuses.count("reading"),
        "finished": statuses.count("finished"),
    }


@app.get("/books/{book_id}", response_model=BookRead, tags=["books"], summary="Get a book", responses=NOT_FOUND)
def read_book(book_id: BookId):
    """Return a single book by its id."""
    return find_book(book_id)


@app.post(
    "/books",
    status_code=201,
    response_model=BookRead,
    tags=["books"],
    summary="Add a book",
    response_description="The book that was added, including its generated id.",
)
def create_book(new_book: BookCreate):
    """Add a book to the reading list. If you leave out the status, the book starts as `to_read`."""
    next_id = max((book["id"] for book in BOOKS), default=0) + 1
    record = BookRecord(id=next_id, **new_book.model_dump(), added_by=CURRENT_USER)
    BOOKS.append(record.model_dump())
    return record


@app.put("/books/{book_id}", response_model=BookRead, tags=["books"], summary="Replace a book", responses=NOT_FOUND)
def replace_book(book_id: BookId, new_book: BookCreate):
    """Replace every field of a book. Fields you leave out go back to their defaults."""
    book = find_book(book_id)
    book.update(new_book.model_dump())
    return book


@app.patch("/books/{book_id}", response_model=BookRead, tags=["books"], summary="Update a book", responses=NOT_FOUND)
def update_book(book_id: BookId, changes: BookUpdate):
    """Change only the fields you send. Every other field keeps its current value."""
    book = find_book(book_id)
    book.update(changes.model_dump(exclude_none=True))
    return book


@app.delete("/books/{book_id}", status_code=204, tags=["books"], summary="Delete a book", responses=NOT_FOUND)
def delete_book(book_id: BookId):
    """Remove a book from the list. The response has no body."""
    book = find_book(book_id)
    BOOKS.remove(book)


@app.post(
    "/books/bulk",
    status_code=201,
    response_model=list[BookRead],
    tags=["books"],
    summary="Add several books",
)
def create_books(new_books: Annotated[list[BookCreate], Body(min_length=1, max_length=20)]):
    """Add up to 20 books in one request. If any book is invalid, none of them are added."""
    records = []
    next_id = max((book["id"] for book in BOOKS), default=0) + 1
    for offset, new_book in enumerate(new_books):
        records.append(BookRecord(id=next_id + offset, **new_book.model_dump(), added_by=CURRENT_USER))
    BOOKS.extend(record.model_dump() for record in records)
    return records


@app.get("/books/{book_id}/notes", response_model=list[Note], tags=["notes"], summary="List notes", responses=NOT_FOUND)
def list_notes(book_id: BookId):
    """Return every note attached to a book."""
    return find_book(book_id)["notes"]


@app.post(
    "/books/{book_id}/notes",
    status_code=201,
    response_model=Note,
    tags=["notes"],
    summary="Add a note",
    responses=NOT_FOUND,
)
def create_note(book_id: BookId, note: Note):
    """Attach a note to a page of a book."""
    book = find_book(book_id)
    if book["pages"] is not None and note.page > book["pages"]:
        raise HTTPException(status_code=422, detail=f"This book only has {book['pages']} pages")
    book["notes"].append(note.model_dump())
    return note
