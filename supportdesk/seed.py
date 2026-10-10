from sqlalchemy import select

from database import SessionLocal
from models import Ticket, TicketPriority, TicketStatus, User, UserRole

PLACEHOLDER_HASH = "seed-placeholder-not-a-real-hash"

users = [
    User(email="priya.nair@example.com", full_name="Priya Nair", hashed_password=PLACEHOLDER_HASH),
    User(email="daniel.okafor@example.com", full_name="Daniel Okafor", hashed_password=PLACEHOLDER_HASH),
    User(email="marta.kowalski@example.com", full_name="Marta Kowalski", hashed_password=PLACEHOLDER_HASH),
    User(email="liam.fischer@supportdesk.example", full_name="Liam Fischer", hashed_password=PLACEHOLDER_HASH, role=UserRole.AGENT),
    User(email="sofia.alvarez@supportdesk.example", full_name="Sofia Alvarez", hashed_password=PLACEHOLDER_HASH, role=UserRole.AGENT),
]

with SessionLocal() as db:
    if db.scalars(select(User)).first() is not None:
        print("Database already has data, nothing to do.")
    else:
        db.add_all(users)
        db.flush()
        priya, daniel, marta, liam, sofia = users
        db.add_all(
            [
                Ticket(title="Cannot reset my password", description="The reset email never arrives, even after checking spam.", customer_id=priya.id),
                Ticket(title="Invoice shows the wrong billing address", description="Our October invoice still lists the old office in Leeds.", priority=TicketPriority.HIGH, customer_id=daniel.id, assignee_id=liam.id, status=TicketStatus.IN_PROGRESS),
                Ticket(title="Export to CSV downloads an empty file", description="The export button finishes, but the file has only the header row.", priority=TicketPriority.HIGH, customer_id=marta.id, assignee_id=sofia.id, status=TicketStatus.IN_PROGRESS),
                Ticket(title="Dark mode would be great", description="Working late, the white dashboard is hard on the eyes.", priority=TicketPriority.LOW, customer_id=priya.id),
                Ticket(title="Site is down for the whole team", description="Everyone gets a 502 error since 09:15 this morning.", priority=TicketPriority.URGENT, customer_id=daniel.id, assignee_id=liam.id),
                Ticket(title="How do I add a teammate?", description="I cannot find where to invite a new member to our workspace.", customer_id=marta.id, assignee_id=sofia.id, status=TicketStatus.RESOLVED),
            ]
        )
        db.commit()
        print("Seeded 5 users and 6 tickets.")
