from typing import Type
from uuid import UUID

import sqlalchemy as sa

from pydantic_table.table_model.model import TableModel
import pydantic_table.sqlalchemy as sap


def Table(
    table: Type[TableModel],
    autoload_with: sa.Engine | sa.Connection | None = None,
) -> sa.Table:
    """
    Get sqlalchemy table based on given table name or schema.

    Declare UUID columns explicitly to avoid potential issues with
        how each dialect interprets UUID type.
    """
    metadata = sa.MetaData()

    table_auto = sa.Table(table.table_name(), metadata, autoload_with=autoload_with)

    declared_columns = (
        [
            sap.Column(col_name, col_info, dialect=autoload_with.dialect.name)
            for col_name, col_info in table.column_fields().items()
            if col_info.get_type() is UUID and col_name in table_auto.c
        ]
        if autoload_with is not None
        else []
    )
    ret = sa.Table(
        table.table_name(),
        metadata,
        *declared_columns,
        autoload_with=autoload_with,
        extend_existing=True,
    )
    return ret
