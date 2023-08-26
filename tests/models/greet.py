from sqlalchemy import (
    Column,
    Index,
    Integer,
    Text,
)

from .meta import Base


class Greet(Base):
    __tablename__ = 'greet'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    message = Column(Integer)


Index('my_index', Greet.name, unique=True, mysql_length=255)
