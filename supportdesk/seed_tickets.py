from sqlalchemy import func, select

from database import SessionLocal
from models import Ticket, TicketPriority, TicketStatus, User, UserRole

L, N, H, U = TicketPriority.LOW, TicketPriority.NORMAL, TicketPriority.HIGH, TicketPriority.URGENT
OPEN, WORK, DONE = TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED

tickets = [
    ("Password reset link expires too fast", "The link is already invalid when I open the email.", N, OPEN),
    ("Invoice PDF is missing the VAT number", "Our accountant needs the VAT number on every invoice.", H, WORK),
    ("Cannot invite a teammate by email", "The invite button does nothing for new addresses.", N, OPEN),
    ("Export to CSV is very slow", "Exporting a month of data takes more than ten minutes.", N, WORK),
    ("Dashboard charts do not load", "The charts spin forever on the reports page.", H, OPEN),
    ("Request: single sign-on with Google", "We would like to log in with our company accounts.", L, OPEN),
    ("Billing page shows the wrong currency", "We pay in euros but the page shows dollars.", N, DONE),
    ("API returns 500 on large uploads", "Uploading a file over 20 MB fails with a server error.", U, WORK),
    ("Typo on the pricing page", "The Team plan says 'unlimted' users.", L, DONE),
    ("Two-factor codes never arrive", "SMS codes take over five minutes, sometimes more.", H, OPEN),
    ("Cannot change the workspace name", "The save button is greyed out in settings.", N, OPEN),
    ("Notification emails go to spam", "All your emails land in our spam folder.", N, DONE),
    ("Mobile layout cuts off the menu", "On a phone the right side of the menu is hidden.", L, OPEN),
    ("Refund for a duplicate charge", "We were charged twice on the 3rd of October.", U, WORK),
    ("Search ignores accented letters", "Searching for 'José' finds nothing.", L, OPEN),
    ("Webhook retries fill our logs", "Failed webhooks are retried every second.", H, OPEN),
    ("Can we export all comments?", "We need a full backup of ticket comments.", N, OPEN),
    ("Login page is slow in the morning", "It takes about 20 seconds to sign in around 9 am.", N, DONE),
]

with SessionLocal() as db:
    if db.scalar(select(func.count()).select_from(Ticket)) >= 20:
        print("Already enough tickets, nothing to do.")
    else:
        customers = db.scalars(select(User).where(User.role == UserRole.CUSTOMER).order_by(User.id)).all()
        agents = db.scalars(select(User).where(User.role == UserRole.AGENT).order_by(User.id)).all()
        for number, (title, description, priority, status) in enumerate(tickets):
            assignee = None if status == OPEN else agents[number % len(agents)]
            db.add(
                Ticket(
                    title=title,
                    description=description,
                    priority=priority,
                    status=status,
                    customer_id=customers[number % len(customers)].id,
                    assignee_id=assignee.id if assignee else None,
                )
            )
        db.commit()
        print(f"Added {len(tickets)} tickets.")
