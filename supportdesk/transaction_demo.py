from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import Ticket


def ticket_count(session):
    return session.scalar(select(func.count()).select_from(Ticket))


writer = SessionLocal()
observer = SessionLocal()

print("Tickets at the start:", ticket_count(observer))

printer = Ticket(
    title="Office printer shows offline",
    description="Everyone on the second floor sees the printer as offline since this morning.",
    customer_id=1,
)
writer.add(printer)
print("After add, the ticket id is", printer.id)

writer.flush()
print("After flush, the ticket id is", printer.id)
print("The writer sees", ticket_count(writer), "tickets, the observer sees", ticket_count(observer))

writer.commit()
print("After commit, the observer sees", ticket_count(observer))

scanner = Ticket(
    title="Document scanner keeps jamming",
    description="The scanner jams on the third page of every multi-page document.",
    customer_id=1,
)
writer.add(scanner)
writer.flush()
print("Flushed a second ticket, the writer sees", ticket_count(writer))
writer.rollback()
print("After rollback, the writer sees", ticket_count(writer), "and the observer sees", ticket_count(observer))

orphan = Ticket(title="Ticket for nobody", description="This customer does not exist.", customer_id=999)
writer.add(orphan)
try:
    writer.flush()
except IntegrityError as error:
    print("The database refused it:", type(error.orig).__name__)

try:
    ticket_count(writer)
except Exception as error:
    print("The session is blocked:", type(error).__name__)

writer.rollback()
print("After rollback, the writer sees", ticket_count(writer))

writer.delete(printer)
writer.commit()
print("Cleaned up, the observer sees", ticket_count(observer))

writer.close()
observer.close()
