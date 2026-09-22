from typing import Optional

from sqlalchemy.orm import DeclarativeBase
from pydantic import Field


from pydantic_table import ColumnField, TableModel
from pydantic_table.sqlalchemy import BaseMeta


class Base(DeclarativeBase):
    pass


class ExampleTable(TableModel, table_name="examples"):
    id: int = ColumnField(description="ID", primary_key=True)
    name: str = ColumnField(description="Name")
    value: Optional[float] = ColumnField(description="Nullable value")


class ExampleTableBase(Base, metaclass=BaseMeta, model=ExampleTable):
    pass
