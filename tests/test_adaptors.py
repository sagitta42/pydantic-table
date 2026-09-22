from typing import Optional

from pydantic_table.table_model.field import ColumnField
from pydantic_table.table_model.model import TableModel

import sqlalchemy as sa
import pydantic_table.sqlalchemy as sap

from pydantic_table.logger import logg


def test_pt2sa():
    class ExampleTable(TableModel, table_name="examples"):
        id: int = ColumnField(description="ID", primary_key=True)
        name: str = ColumnField(description="Name")
        value: Optional[float] = ColumnField(description="Nullable value")

    column_fields = ExampleTable.column_fields()
    logg.debug(column_fields)
    column_info = column_fields["value"]
    logg.debug(column_info)

    sa_column = sap.Column("value", column_info)
    logg.debug(sa_column)


def test_sa2pt():
    sa_column = sa.Column("id", sa.String(), nullable=True)
    logg.debug(sa_column)

    column_info = sap.ColumnFieldInfo(sa_column)
    logg.debug(column_info)
    logg.debug(column_info.annotation)
    logg.debug(column_info.get_type())
    logg.debug(column_info.nullable)
