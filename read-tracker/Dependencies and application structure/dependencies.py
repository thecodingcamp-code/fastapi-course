from typing import Annotated

from fastapi import Depends, HTTPException, Path, Query

from config import get_settings
from data import BOOKS, CURRENT_USER, OPEN_SESSIONS, USER_ROLES
from schemas import Status

settings = get_settings()

BookId = Annotated[int, Path(gt=0, description="The id of the book.", examples=[2])]

NOT_FOUND = {404: {"description": "No book exists with this id."}}
EDIT_ERRORS = {**NOT_FOUND, 403: {"description": "The book was added by someone else."}}


def get_book(book_id: BookId):
    for book in BOOKS:
        if book["id"] == book_id:
            return book
    raise HTTPException(status_code=404, detail="Book not found")


FoundBook = Annotated[dict, Depends(get_book)]


def get_current_user():
    return CURRENT_USER


CurrentUser = Annotated[str, Depends(get_current_user)]


def get_current_role(user: CurrentUser):
    return USER_ROLES.get(user, "member")


CurrentRole = Annotated[str, Depends(get_current_role)]


class RoleChecker:
    def __init__(self, allowed_roles: set[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, role: CurrentRole):
        if role not in self.allowed_roles:
            raise HTTPException(status_code=403, detail="This action needs a higher role")


require_admin = RoleChecker({"admin"})


def get_editable_book(book: FoundBook, user: CurrentUser, role: CurrentRole):
    if book["added_by"] != user and role != "admin":
        raise HTTPException(status_code=403, detail="You can only change books you added")
    return book


EditableBook = Annotated[dict, Depends(get_editable_book)]


class Session:
    def __init__(self, books: list[dict]):
        self.books = books
        self.added = []
        OPEN_SESSIONS.append(self)

    def next_id(self):
        return max((book["id"] for book in self.books), default=0) + 1

    def has_isbn(self, isbn: str):
        return any(book["isbn"] == isbn for book in self.books)

    def add(self, record: dict):
        self.books.append(record)
        self.added.append(record)

    def commit(self):
        self.added.clear()

    def rollback(self):
        for record in self.added:
            self.books.remove(record)
        self.added.clear()

    def close(self):
        OPEN_SESSIONS.remove(self)


def get_session():
    session = Session(BOOKS)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session, scope="function")]


def get_pagination(
    skip: Annotated[int, Query(ge=0, description="How many items to skip.")] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=settings.max_page_size, description="The maximum number of items to return."),
    ] = settings.default_page_size,
):
    return {"skip": skip, "limit": limit}


PageParams = Annotated[dict, Depends(get_pagination)]


def get_book_filters(
    status: Annotated[Status | None, Query(description="Only return books with this reading status.")] = None,
    author: Annotated[
        str | None,
        Query(min_length=2, max_length=50, description="Only return books whose author contains this text, ignoring case."),
    ] = None,
    tag: Annotated[str | None, Query(max_length=30, description="Only return books with this tag.")] = None,
    min_rating: Annotated[int | None, Query(ge=1, le=5, description="Only return books rated at least this high.")] = None,
):
    results = BOOKS
    if status is not None:
        results = [book for book in results if book["status"] == status]
    if author is not None:
        results = [book for book in results if author.lower() in book["author"].lower()]
    if tag is not None:
        results = [book for book in results if tag.lower() in book["tags"]]
    if min_rating is not None:
        results = [book for book in results if book["rating"] is not None and book["rating"] >= min_rating]
    return results


FilteredBooks = Annotated[list[dict], Depends(get_book_filters)]


class BookService:
    def __init__(self, books: FilteredBooks):
        self.books = books

    def page(self, skip: int, limit: int):
        return self.books[skip : skip + limit]

    def stats(self):
        statuses = [book["status"] for book in self.books]
        return {
            "total": len(statuses),
            "to_read": statuses.count("to_read"),
            "reading": statuses.count("reading"),
            "finished": statuses.count("finished"),
        }


BookServiceDep = Annotated[BookService, Depends()]
