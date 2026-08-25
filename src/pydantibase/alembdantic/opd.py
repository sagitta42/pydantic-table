"""
op + pydantic
"""

from alembic import op
import sqlalchemy as sa
from typing import Any, Type

from pydantibase.table_model import TableModel


def create_table(
    table_model: Type[TableModel],
    foreign_keys: dict[str, str] = {},
):
    """
    Invoke alembic create table based on provided TableModel schema.

    primary_keys (list[str]): list of primary key column names
    foreign_keys (dict[str, str]): dictionary mapping {column name: foreign key column information}
        Format of foreign key is foreign_table.column

    Column names must correspond to TableModel field names.
    """
    columns = table_model.get_sa_columns(foreign_keys)
    op.create_table(table_model.table_name(), *columns)


def drop_table(table_model: Type[TableModel]):
    """
    Invoke alembic drop table based on provided TableModel schema.
    """
    op.drop_table(table_model.table_name())


def read_table(table: str | Type[TableModel]) -> sa.Table:
    """
    Get sqlalchemy table based on given table name or schema.
    """
    table_name = table if isinstance(table, str) else table.table_name()
    metadata = sa.MetaData()
    ret = sa.Table(table_name, metadata, autoload_with=op.get_bind())
    return ret


def insert(input: TableModel | list[TableModel]):
    """
    Insert given row(s) to the table corresponding to its schema.

    Read table based on table name.
    Invoke alembic execute() of table insert() with model dump.
    """
    rows = input if isinstance(input, list) else [input]
    for row in rows:
        table = read_table(row.table_name())
        op.execute(table.insert().values(row.model_dump()))


def delete(input: TableModel | list[TableModel]):
    """
    Delete given row(s) from the table corresponding to its schema.

    Read table based on table name.
    Invoke alembic execute() with table delete() matching all fields in where()
    """
    rows = input if isinstance(input, list) else [input]

    for row in rows:
        table = read_table(row.table_name())
        condition = sa.and_(
            *[table.c[column] == value for column, value in row.model_dump().items()]
        )
        op.execute(table.delete().where(condition))


def delete_by(table: Type[TableModel], column: str, value: Any):
    """
    Delete rows from table where column has given value.
    """
    tb = read_table(table.table_name())
    op.execute(tb.delete().where(tb.c[column] == value))


def delete_row_by_id(row: TableModel):
    """
    Delete given row from the table it corresponds to based on ID.

    Applies only to tables that have an ID column.
    """
    if not row.has_id_column:
        raise ValueError(
            f"Table {row.table_name()} does not have an id column! Cannot delete row by ID"
        )
    table = read_table(row.table_name())
    op.execute(table.delete().where(table.c.id == row.id))
