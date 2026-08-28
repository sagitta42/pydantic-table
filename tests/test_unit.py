import json

from pydantic import Field

from pydantic_table.logger import logg
from pydantic_table.table_model.exceptions import PydanticTableTypeError
from pydantic_table.table_model.field import ColumnField
from pydantic_table.table_model.model import TableModel
from tests.conftest import PATH_TO_CONFIGS


def test_model():
    filename = "test_model"

    class ExampleTable(TableModel, table_name="examples"):
        id: int = ColumnField(description="ID", primary_key=True)
        name: str = ColumnField(description="Name")
        value: float = ColumnField(description="Value", nullable=True)

    model_config_path = PATH_TO_CONFIGS / f"{filename}.json"
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
