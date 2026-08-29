import enum
from typing import Type

import sqlalchemy as sa

from pydantic_table import TableModel
import pydantic_table.table_model.field as pt_field


class SaColumnType(enum.Enum):
    """
    Mapping between python types and sqlalchemy TypeEngine types
    """

    int = sa.Integer
    float = sa.Float
    str = sa.String

    @classmethod
    def from_type(cls, t: type):
        return cls[t.__name__].value


class ColumnType(enum.Enum):
    FLOAT = float

    # <class 'sqlalchemy.sql.sqltypes.FLOAT'>
    @classmethod
    def from_sa_type_engine(cls, t: Type[sa.types.TypeEngine]) -> type:
        return cls[t.__name__].value


def get_column_sa_type(
    name: str, table_model: Type[TableModel]
) -> Type[sa.types.TypeEngine]:
    """
    Get sqlalchemy TypeEngine type of given field based on its annotation type.
    """
    column_info = table_model.column_fields()[name]
    assert column_info.annotation is not None
    ret = SaColumnType.from_type(column_info.annotation)
    return ret


def Column(
    name: str, table_model: Type[TableModel], foreign_key: str | None = None
) -> sa.Column:
    foreign_key_args = []
    if foreign_key is not None:
        sa_foreign_key = sa.ForeignKey(
            name=f"fk_{foreign_key.replace('.', '_')}",
            column=foreign_key,
        )
        foreign_key_args.append(sa_foreign_key)

    column_info = table_model.column_fields()[name]
    default = (
        None
        if column_info.is_required() or column_info.default is None
        else column_info.default
    )

    ret = sa.Column(
        name,
        get_column_sa_type(name, table_model),
        nullable=column_info.nullable,
        default=default,
        server_default=default,
        primary_key=column_info.primary_key,
        *foreign_key_args,
    )
    return ret


def ColumnFieldInfo(column: sa.Column) -> pt_field.ColumnFieldInfo:
    """
    Translator from sa.Column to ColumnFieldInfo
    """
    sa_type_engine = type(column.type)
    ret = pt_field.ColumnFieldInfo(
        annotation=ColumnType.from_sa_type_engine(sa_type_engine),
        default=column.default,
        primary_key=column.primary_key,
        nullable=column.nullable,
    )
    return ret
