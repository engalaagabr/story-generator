"""SQLAlchemy metadata; importing this module does not configure a database."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
