"""
op adaptors
"""

from alembic import op
import sqlalchemy as sa
from typing import Any, Type

from pydantic_table.alembic.archive import Archive
from pydantic_table.alembic.exceptions import (
    ArchiveException,
    PydanticTableAlembicException,
)
from pydantic_table.logger import logg
import pydantic_table.sqlalchemy as sap

from pydantic_table.table_model.model import TableModel
from pydantic_table.utils import dict_as_str


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
    archive = Archive()
    # TODO: table rename
    column_fields = (
        archive.read_column_fields(table.table_name())
        if archive.file_exists
        else {
            column_name: column_info
            for column_name, column_info in table.column_fields().items()
            if column_name in columns
        }
    )
    sa_columns = [
        sap.Column(name, column_info, foreign_key=foreign_keys.get(name, None))
        for name, column_info in column_fields.items()
    ]

    op.create_table(table.table_name(), *sa_columns)


def drop_table(table: Type[TableModel]):
    """
    Invoke alembic drop table based on provided TableModel schema.

    If detect extra columns or missing columns i.e. any schema change,
        archive table schema.
    """
    sa_table = sap.Table(table, autoload_with=op.get_bind())
    # TODO: mutual set difference
    # TODO: detect any schema change in column info (changed default, changed nullability or primary)
    model_has_new_columns = any(
        col_name not in table.column_fields() for col_name in sa_table.c
    )
    model_is_missing_columns = any(
        col_name not in sa_table.c for col_name in table.column_fields()
    )
    if model_has_new_columns or model_is_missing_columns:
        Archive().archive_table_model(sa_table)

    op.drop_table(table.table_name())


def update_where(table: Type[TableModel], values: dict[str, Any], **kwargs):
    """
    Update table with given values {column: value}.

    kwargs in format column=value for the where condition
    """
    tb = sap.Table(table, autoload_with=op.get_bind())
    condition = _get_condition(tb, **kwargs)
    logg.debug(f"Values: {dict_as_str(values)}")
    op.execute(tb.update().where(condition).values(values))


def add_column(
    table: Type[TableModel],
    name: str,
    data: list[TableModel] | TableModel = [],
    foreign_key: str | None = None,
):
    """
    Add column to table.

    Given name must be present in table column fields or in archive.
    Fill column with given data; otherwise initialize to column default (must be present).

    In case column is not nullable, no default, and data is given:
        - create column first as nullable to prevent crash
        - add given column data (use other columns for condition)
        - set column back to nullable
    """
    # TODO: always read archived file if exists, even if column exists - could be other schema change
    if name in table.column_fields():
        column_info = table.column_fields()[name]
    else:
        archive = Archive()
        try:
            column_info = archive.read_column_info(name)
        except ArchiveException:
            raise PydanticTableAlembicException(
                f"Column {name} not present in table {table.table_info()} or in archive! Cannot add."
            )

    sa_column = sap.Column(name, column_info, foreign_key=foreign_key)

    logg.debug(f"Adding column - column info: {column_info}")
    logg.debug(
        f"default={column_info.default} default factory={column_info.default_factory} required={column_info.is_required()}"
    )
    # is required = neither default nor default factory are defined
    if not column_info.nullable and column_info.is_required():
        data_list = data if isinstance(data, list) else [data]
        if len(data_list) == 0:
            raise PydanticTableAlembicException(
                f"Column {name} in {table.table_info()} is not nullable and no default was given. You provided no data."
                f"Either provide data to add, or a default; or make column nullable"
            )

        sa_column.nullable = True
        op.add_column(table.table_name(), sa_column)
        for row in data_list:
            logg.debug(f"Adding data row - {row}")
            logg.debug(f"Column dump - {row.column_dump()}")
            logg.debug(f"Data dump - {row.data_dump()}")
            update_where(
                table,
                values={name: row.get(name)},
                **row.column_dump(exclude={name: True}),
            )
        # op.alter_column(table.table_name(), name, nullable=False) - error
        with op.batch_alter_table(table.table_name()) as batch_op:
            batch_op.alter_column(name, nullable=False)
        return

    op.add_column(
        table.table_name(), sap.Column(name, column_info, foreign_key=foreign_key)
    )


def drop_column(table: Type[TableModel], name: str):
    """
    Drop column.

    Drop column from the table.
    Archive column if not present in TableModel anymore
        (schema update removes column)
    """
    if name not in table.column_fields():
        Archive().archive_column_info(table, name)

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
        table = sap.Table(row.table, autoload_with=op.get_bind())

        for col_name in row.missing_columns:
            if col_name in table.c:
                raise PydanticTableAlembicException(
                    f"Row given for table {row.table_name()} is missing column {col_name}!"
                )

        data = row.column_dump()
        logg.debug(f"Inserting data - column dump: {data}")
        data = {col: val for col, val in data.items() if col in table.c}
        logg.debug(f"Inserting data - only columns in table: {data}")

        for col_name, col_value in row.extra_data.items():
            if col_name not in table.c:
                raise PydanticTableAlembicException(
                    f"Row given for table {row.table_info()} has extra column {col_name}!"
                )
            data[col_name] = col_value

        logg.debug(f"Inserting data + extra columns: {data}")
        op.execute(table.insert().values(data))


def delete_where(table: Type[TableModel], **kwargs):
    """
    Delete rows from table where columns have given values.

    kwargs in format column=value for the where condition.
    """
    tb = sap.Table(table, autoload_with=op.get_bind())
    condition = _get_condition(tb, **kwargs)
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


def _get_condition(tb: sa.Table, **kwargs) -> sa.ColumnElement[bool]:
    logg.debug(f"Condition: {dict_as_str(kwargs)}")
    condition = sa.and_(*[tb.c[column] == value for column, value in kwargs.items()])
    return condition
