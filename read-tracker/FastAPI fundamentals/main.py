from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel, Field

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
    ],
)

BOOKS = [
    {"id": 1, "title": "Atomic Habits", "author": "James Clear", "status": "finished", "added_by": "maya.chen@example.com"},
    {"id": 2, "title": "Deep Work", "author": "Cal Newport", "status": "reading", "added_by": "maya.chen@example.com"},
    {"id": 3, "title": "The Pragmatic Programmer", "author": "David Thomas", "status": "to_read", "added_by": "maya.chen@example.com"},
    {"id": 4, "title": "Sapiens", "author": "Yuval Noah Harari", "status": "finished", "added_by": "maya.chen@example.com"},
    {"id": 5, "title": "Project Hail Mary", "author": "Andy Weir", "status": "reading", "added_by": "maya.chen@example.com"},
]

BookId = Annotated[int, Path(gt=0, description="The id of the book.", examples=[2])]

NOT_FOUND = {404: {"description": "No book exists with this id."}}


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200, description="The title of the book.", examples=["Deep Work"])
    author: str = Field(min_length=1, max_length=100, description="The name of the author.", examples=["Cal Newport"])
    status: Literal["to_read", "reading", "finished"] = Field(
        default="to_read", description="Where the book is in your reading list."
    )


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200, description="A new title.")
    author: str | None = Field(default=None, min_length=1, max_length=100, description="A new author.")
    status: Literal["to_read", "reading", "finished"] | None = Field(default=None, description="A new status.")


class BookPublic(BaseModel):
    id: int
    title: str
    author: str
    status: Literal["to_read", "reading", "finished"]


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


@app.get("/books", response_model=list[BookPublic], tags=["books"], summary="List books")
def list_books(
    status: Annotated[
        Literal["to_read", "reading", "finished"] | None,
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


@app.get("/books/{book_id}", response_model=BookPublic, tags=["books"], summary="Get a book", responses=NOT_FOUND)
def read_book(book_id: BookId):
    """Return a single book by its id."""
    return find_book(book_id)


@app.post(
    "/books",
    status_code=201,
    response_model=BookPublic,
    tags=["books"],
    summary="Add a book",
    response_description="The book that was added, including its generated id.",
)
def create_book(new_book: BookCreate):
    """Add a book to the reading list. If you leave out the status, the book starts as `to_read`."""
    next_id = max((book["id"] for book in BOOKS), default=0) + 1
    book = {"id": next_id, **new_book.model_dump(), "added_by": "maya.chen@example.com"}
    BOOKS.append(book)
    return book


@app.put("/books/{book_id}", response_model=BookPublic, tags=["books"], summary="Replace a book", responses=NOT_FOUND)
def replace_book(book_id: BookId, new_book: BookCreate):
    """Replace every field of a book. Fields you leave out go back to their defaults."""
    book = find_book(book_id)
    book.update(new_book.model_dump())
    return book


@app.patch("/books/{book_id}", response_model=BookPublic, tags=["books"], summary="Update a book", responses=NOT_FOUND)
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