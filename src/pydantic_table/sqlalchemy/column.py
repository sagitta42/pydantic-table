import datetime
import enum
from typing import Optional, Type

import sqlalchemy as sa

import pydantic_table.table_model.field as pt_field


class SaColumnType(enum.Enum):
    """
    Mapping between python types and sqlalchemy TypeEngine types
    """

    int = sa.Integer
    float = sa.Float
    str = sa.String
    date = sa.Date
    bool = sa.Boolean

    @classmethod
    def from_type(cls, t: type):
        return cls[t.__name__].value


class ColumnType(enum.Enum):
    FLOAT = float
    Integer = int
    INTEGER = int
    String = str
    VARCHAR = str
    DOUBLE_PRECISION = float
    DATE = datetime.date

    # <class 'sqlalchemy.sql.sqltypes.FLOAT'>
    @classmethod
    def from_sa_type_engine(cls, t: Type[sa.types.TypeEngine]) -> type:
        return cls[t.__name__].value


def Column(
    name: str, column_info: pt_field.ColumnFieldInfo, foreign_key: str | None = None
) -> sa.Column:
    foreign_key_args = []
    if foreign_key is not None:
        sa_foreign_key = sa.ForeignKey(
            foreign_key,
            name=f"fk_{foreign_key.replace('.', '_')}",
        )
        foreign_key_args.append(sa_foreign_key)

    default = None if column_info.is_required() else column_info.default

    col_type = column_info.get_type()
    server_default = (
        sa.true() if default else sa.false() if col_type is bool else default
    )

    ret = sa.Column(
        name,
        SaColumnType.from_type(col_type),
        *foreign_key_args,
        nullable=column_info.nullable,
        default=default,
        server_default=server_default,
        primary_key=column_info.primary_key,
    )
    return ret


def ColumnFieldInfo(column: sa.Column) -> pt_field.ColumnFieldInfo:
    """
    Translator from sa.Column to ColumnFieldInfo.

    Note that default=None in sa.Column means "no default" and not "default is null".
    While in ColumnFieldInfo, default=None means "default is null", while PydanticUndefined means "no default".
    Avoid the default= ketword argument to produce PydanticUndefined.
    """
    sa_type_engine = type(column.type)
    column_type = ColumnType.from_sa_type_engine(sa_type_engine)
    annotation = Optional[column_type] if column.nullable else column_type
    kwargs = {}
    # TODO: does SQLAlchemy differentiate between default=None (nullable) and "default undefined"
    if column.default is not None:
        kwargs["default"] = column.default

    ret = pt_field.ColumnFieldInfo(
        annotation=annotation,
        # TODO: save/get description in table metadata
        # description=column.name,
        primary_key=column.primary_key,
        **kwargs,
    )
    return ret
