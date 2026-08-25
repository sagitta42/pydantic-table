from typing import Literal

from pydantic import Field

from pydantibase import TableModel
from pydantibase.sqlalchemic import BaseMeta, Base


class ExampleTable(TableModel):
    table_name_: Literal["examples"] = Field(
        default="examples", description="Table name", exclude=True
    )
    primary_keys_: list[str] = Field(
        default=["id"], description="Primary keys", exclude=True
    )
    id: int = Field(description="ID")
    name: str = Field(description="Name")
    value: float = Field(description="Value")


class ExampleTableBase(Base, metaclass=BaseMeta, model=ExampleTable):
    pass
