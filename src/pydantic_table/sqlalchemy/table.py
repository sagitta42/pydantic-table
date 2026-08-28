from typing import Type

import sqlalchemy as sa

from pydantic_table.table_model.model import TableModel


def Table(
    table: str | Type[TableModel],
    autoload_with: sa.Engine | sa.Connection | None = None,
) -> sa.Table:
    """
    Get sqlalchemy table based on given table name or schema.
    """
    metadata = sa.MetaData()
    table_name = table if isinstance(table, str) else table.table_name()
    ret = sa.Table(table_name, metadata, autoload_with=autoload_with)
    return ret
