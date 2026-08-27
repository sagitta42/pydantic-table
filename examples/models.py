from pydantic import Field

from pydantic_table import TableModel
from pydantic_table.sqlalchemy import BaseMeta, Base


class ExampleTable(TableModel, table_name="examples", primary_keys=["id"]):
    id: int = Field(description="ID")
    name: str = Field(description="Name")
    value: float = Field(description="Value")


class ExampleTableBase(Base, metaclass=BaseMeta, model=ExampleTable):
    pass
