"""
op + pydantic
"""

from alembic import op
import sqlalchemy as sa
from typing import Any, Type

from pydantic_table.alembic.exceptions import PydanticTalbeAlembicException
import pydantic_table.sqlalchemy as sap

from pydantic_table.table_model.model import TableModel


def create_table(
    table: Type[TableModel],
    columns: list[str],
    foreign_keys: dict[str, str] = {},
):
    """
    Invoke alembic create table based on provided TableModel schema.

    primary_keys (list[str]): list of primary key column names
    foreign_keys (dict[str, str]): dictionary mapping {column name: foreign key column information}
        Format of foreign key is foreign_table.column

    Column names must correspond to TableModel field names.
    """
    sa_columns = [
        sap.Column(name, table, foreign_key=foreign_keys.get(name, None))
        for name in columns
    ]
    op.create_table(table.table_name(), *sa_columns)


def drop_table(table: Type[TableModel]):
    """
    Invoke alembic drop table based on provided TableModel schema.
    """
    op.drop_table(table.table_name())


def add_column(table: Type[TableModel], name: str, foreign_key: str | None = None):
    """
    Add column
    """
    if name not in table.column_fields():
        raise PydanticTalbeAlembicException(
            f"Column {name} not present in {table.table_info()}! Cannot add."
        )

    op.add_column(table.table_name(), sap.Column(name, table, foreign_key=foreign_key))


def drop_column(table: Type[TableModel], name: str):
    op.drop_column(table.table_name(), name)


def insert(rows: TableModel | list[TableModel]):
    """
    Insert given row(s) to the table corresponding to its schema.

    Read table based on table name.
    Invoke alembic execute() of table insert() with model dump.

    Account for backwards compatibility with added columns or dropped columns.

    Check existing columns in input that were not given (missing columns):
        - if not present in table, ignore (past/future schema change dropped/added this column)
        - if present in table, raise error (must be given but was not)

    Ignore columns that are not present in table.

    Check hidden extra columns in input (extra columns):
        - if present in table, include (past/future schema change added/dropped this column)
        - if not present in table, raise error (non-existing columns were given)
    """
    row_list = rows if isinstance(rows, list) else [rows]
    for row in row_list:
        table = sap.Table(row.table)

        for col_name in row.missing_columns:
            if col_name in table.c:
                raise PydanticTalbeAlembicException(
                    f"Row given for table {row.table_name()} is missing column {col_name}!"
                )

        data = {col: val for col, val in row.column_dump().items() if col in table.c}

        for col_name, col_value in row.extra_data.items():
            if col_name not in table.c:
                raise PydanticTalbeAlembicException(
                    f"Row given for table {row.table_info()} has extra column {col_name}!"
                )
            data[col_name] = col_value

        op.execute(table.insert().values(data))


def delete_where(table: Type[TableModel], **kwargs):
    """
    Delete rows from table where columns have given values.

    kwargs in format column=value.
    """
    tb = sap.Table(table)
    condition = sa.and_(*[tb.c[column] == value for column, value in kwargs.items()])
    op.execute(tb.delete().where(condition))


def deep_delete(rows: TableModel | list[TableModel]):
    """
    Delete given row(s) from the table corresponding to its schema.

    Read table based on table name.
    Invoke alembic execute() with table delete() matching all fields in where().

    Note that this operation takes a lot of time, but is the most secure as it deletes exactly the row.
    """
    row_list = rows if isinstance(rows, list) else [rows]
    table = row_list[0].table

    for row in row_list:
        delete_where(table, **row.data_dump())
