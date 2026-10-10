from fastapi import FastAPI

from config import SettingsDep, get_settings
from routers import admin, books, notes

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="""
Keep track of the books you are reading.

* Browse and filter your reading list
* Add, update, and remove books
* Every book has a status: `to_read`, `reading`, or `finished`
""",
    version="1.0.0",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
    contact={"name": "Reading Tracker Support", "email": "support@readingtracker.example"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    openapi_tags=[
        {"name": "service", "description": "Basic information about the API itself."},
        {"name": "books", "description": "Create, read, update, and delete books in the reading list."},
        {"name": "notes", "description": "Notes attached to pages of a book."},
        {"name": "admin", "description": "Reports that only admins can see."},
    ],
)

app.include_router(books.router)
app.include_router(notes.router)
app.include_router(admin.router)


@app.get("/", tags=["service"], summary="API status")
def read_root(settings: SettingsDep):
    """Check that the API is up and see which version is running."""
    return {
        "service": settings.app_name,
        "environment": settings.environment,
        "version": "1.0.0",
        "status": "running",
    }
