from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from models import Base

for table in Base.metadata.sorted_tables:
    print(CreateTable(table).compile(dialect=postgresql.dialect()))
