import json

from pydantic import Field

from examples.models import ExampleTable
from pydantic_table.logger import logg
from pydantic_table.table_model.exceptions import PydanticTableTypeError
from pydantic_table.table_model.field import ColumnField, ColumnFieldInfo
from pydantic_table.table_model.model import TableModel
from tests.conftest import PATH_TO_CONFIGS

filename = "test_model"
model_config_path = PATH_TO_CONFIGS / f"{filename}.json"


def test_model():
    with open(model_config_path) as f:
        model = ExampleTable(**json.load(f))

    logg.debug("Example table")
    logg.debug(model)


def test_bad_model():
    try:

        class BadTable(TableModel, table_name="examples"):
            id: int = ColumnField(description="ID", primary_key=True)
            name: str = Field(description="Name")  # not allowed
            value: float = ColumnField(description="Value")

    except PydanticTableTypeError as e:
        logg.debug(e)


def test_column_field():
    column_info = ExampleTable.column_fields()["id"]
    dct = column_info.as_dict()

    logg.debug("Serialized")
    logg.debug(dct)

    rev_info = ColumnFieldInfo(**dct)
    logg.debug("Re-Serialized")
    logg.debug(rev_info)


def test_row():
    row = ExampleTable(id=42, name="Alice", value=1.618, new_column="foo")
    logg.debug(row.model_dump())
    logg.debug(row.column_dump())
    logg.debug(row.data_dump())
