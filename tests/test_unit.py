import json

from pydantic import Field

from pydantic_table.logger import logg
from pydantic_table.table_model.model import TableModel
from tests.conftest import PATH_TO_CONFIGS


def test_model():
    filename = "test_model"

    class ExampleTable(TableModel, table_name="examples", primary_keys=["id"]):
        id: int = Field(description="ID")
        name: str = Field(description="Name")
        value: float = Field(description="Value")    

    model_config_path = PATH_TO_CONFIGS / f"{filename}.json"
    with open(model_config_path) as f:
        model = ExampleTable(**json.load(f))

    logg.debug("Example table")
    logg.debug(model)
