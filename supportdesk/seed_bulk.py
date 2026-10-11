from sqlalchemy import func, select, text

from database import SessionLocal
from models import Ticket

TOTAL = 200_000

with SessionLocal() as db:
    if db.scalar(select(func.count()).select_from(Ticket)) >= TOTAL:
        print("Bulk tickets already added.")
    else:
        db.execute(
            text(
                """
                INSERT INTO tickets (title, description, status, priority, customer_id, assignee_id, created_at, updated_at)
                SELECT
                    'Bulk ticket ' || n,
                    'Generated ticket number ' || n,
                    (CASE WHEN n % 20 = 0 THEN 'OPEN' WHEN n % 20 = 1 THEN 'IN_PROGRESS'
                          WHEN n % 3 = 0 THEN 'RESOLVED' ELSE 'CLOSED' END)::ticketstatus,
                    (ARRAY['LOW', 'NORMAL', 'NORMAL', 'HIGH', 'URGENT'])[1 + n % 5]::ticketpriority,
                    1 + n % 3,
                    4 + n % 2,
                    now() - make_interval(mins => n),
                    now() - make_interval(mins => n)
                FROM generate_series(1, :total) AS n
                """
            ),
            {"total": TOTAL},
        )
        db.execute(text("ANALYZE tickets"))
        db.commit()
        print(f"Added {TOTAL} tickets.")
