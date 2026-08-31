from pydantic_table.table_model.field import ColumnField
from pydantic_table.table_model.model import TableModel

import sqlalchemy as sa
import pydantic_table.sqlalchemy as sap

from pydantic_table.logger import logg

def test_pt2sa():
    class ExampleTable(TableModel, table_name="examples"):
        id: int = ColumnField(description="ID", primary_key=True)
        name: str = ColumnField(description="Name")
        value: float = ColumnField(description="Value", nullable=True)

    column_info = ExampleTable.column_fields()["name"]
    logg.debug(column_info)

    sa_column = sap.Column("id", column_info)
    logg.debug(sa_column)

def test_sa2pt():
    sa_column = sa.Column("id", sa.String(), nullable=False)
    logg.debug(sa_column)

    column_info = sap.ColumnFieldInfo(sa_column)
    logg.debug(column_info)
