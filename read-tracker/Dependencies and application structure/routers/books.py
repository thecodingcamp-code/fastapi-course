from typing import Annotated

from fastapi import APIRouter, Body, HTTPException

from config import get_settings
from data import BOOKS
from dependencies import (
    EDIT_ERRORS,
    NOT_FOUND,
    BookServiceDep,
    CurrentUser,
    EditableBook,
    FoundBook,
    PageParams,
    Session,
    SessionDep,
)
from schemas import BookCreate, BookRead, BookRecord, BookUpdate

router = APIRouter(prefix="/books", tags=["books"])

settings = get_settings()


def add_book(session: Session, new_book: BookCreate, user: str):
    if new_book.isbn is not None and session.has_isbn(new_book.isbn):
        raise HTTPException(status_code=409, detail=f"A book with ISBN {new_book.isbn} already exists")
    record = BookRecord(id=session.next_id(), **new_book.model_dump(), added_by=user)
    session.add(record.model_dump())
    return record


@router.get("", response_model=list[BookRead], summary="List books")
def list_books(service: BookServiceDep, page: PageParams):
    """Return the reading list, optionally filtered by status, author, tag, or minimum rating."""
    return service.page(page["skip"], page["limit"])


@router.get("/stats", summary="Reading statistics")
def read_book_stats(service: BookServiceDep):
    """Count the books in the list, in total and for each reading status. Accepts the same filters as the list."""
    return service.stats()


@router.get("/{book_id}", response_model=BookRead, summary="Get a book", responses=NOT_FOUND)
def read_book(book: FoundBook):
    """Return a single book by its id."""
    return book


@router.post(
    "",
    status_code=201,
    response_model=BookRead,
    summary="Add a book",
    response_description="The book that was added, including its generated id.",
)
def create_book(new_book: BookCreate, user: CurrentUser, session: SessionDep):
    """Add a book to the reading list. If you leave out the status, the book starts as `to_read`."""
    return add_book(session, new_book, user)


@router.put("/{book_id}", response_model=BookRead, summary="Replace a book", responses=EDIT_ERRORS)
def replace_book(book: EditableBook, new_book: BookCreate):
    """Replace every field of a book. Fields you leave out go back to their defaults."""
    book.update(new_book.model_dump())
    return book


@router.patch("/{book_id}", response_model=BookRead, summary="Update a book", responses=EDIT_ERRORS)
def update_book(book: EditableBook, changes: BookUpdate):
    """Change only the fields you send. Every other field keeps its current value."""
    book.update(changes.model_dump(exclude_none=True))
    return book


@router.delete("/{book_id}", status_code=204, summary="Delete a book", responses=EDIT_ERRORS)
def delete_book(book: EditableBook):
    """Remove a book from the list. The response has no body."""
    BOOKS.remove(book)


@router.post("/bulk", status_code=201, response_model=list[BookRead], summary="Add several books")
def create_books(
    new_books: Annotated[list[BookCreate], Body(min_length=1, max_length=settings.max_bulk_size)],
    user: CurrentUser,
    session: SessionDep,
):
    """Add several books in one request. If any book fails, none of them are added."""
    return [add_book(session, new_book, user) for new_book in new_books]
