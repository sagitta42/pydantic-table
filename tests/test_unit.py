import json

from pydantic import Field

from pydantic_table.logger import logg
from pydantic_table.table_model.exceptions import PydanticTableTypeError
from pydantic_table.table_model.field import ColumnField, ColumnFieldInfo
from pydantic_table.table_model.model import TableModel
from tests.conftest import PATH_TO_CONFIGS

filename = "test_model"
model_config_path = PATH_TO_CONFIGS / f"{filename}.json"


def test_model():
    class ExampleTable(TableModel, table_name="examples"):
        id: int = ColumnField(description="ID", primary_key=True)
        name: str = ColumnField(description="Name")
        value: float = ColumnField(description="Value", nullable=True)

    with open(model_config_path) as f:
        model = ExampleTable(**json.load(f))

    logg.debug("Example table")
    logg.debug(model)


def test_bad_model():
    try:

        class ExampleTable(TableModel, table_name="examples"):
            id: int = ColumnField(description="ID", primary_key=True)
            name: str = Field(description="Name")  # not allowed
            value: float = ColumnField(description="Value")

    except PydanticTableTypeError as e:
        logg.debug(e)

def test_column_field():
    filename = "test_model"

    class ExampleTable(TableModel, table_name="examples"):
        id: int = ColumnField(description="ID", primary_key=True)
        name: str = ColumnField(description="Name")
        value: float = ColumnField(description="Value", nullable=True)

    column_info = ExampleTable.column_fields()["id"]
    dct = column_info.as_dict()

    logg.debug("Serialized")
    logg.debug(dct)

    rev_info = ColumnFieldInfo(**dct)
    logg.debug("Re-Serialized")
    logg.debug(rev_info)
