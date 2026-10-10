from fastapi import APIRouter, HTTPException

from dependencies import EDIT_ERRORS, NOT_FOUND, EditableBook, FoundBook, PageParams
from schemas import Note

router = APIRouter(prefix="/books/{book_id}/notes", tags=["notes"])


@router.get("", response_model=list[Note], summary="List notes", responses=NOT_FOUND)
def list_notes(book: FoundBook, page: PageParams):
    """Return the notes attached to a book."""
    return book["notes"][page["skip"] : page["skip"] + page["limit"]]


@router.post("", status_code=201, response_model=Note, summary="Add a note", responses=EDIT_ERRORS)
def create_note(book: EditableBook, note: Note):
    """Attach a note to a page of a book."""
    if book["pages"] is not None and note.page > book["pages"]:
        raise HTTPException(status_code=422, detail=f"This book only has {book['pages']} pages")
    book["notes"].append(note.model_dump())
    return note
