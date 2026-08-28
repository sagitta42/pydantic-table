import enum
from typing import TYPE_CHECKING, ClassVar, Self, Type

import sqlalchemy as sa
from pydantic import BaseModel, model_validator

from pydantic_table.logger import logg
from pydantic_table.table_model.field import ColumnFieldInfo
from pydantic_table.table_model.internal_attr import InternalAttr
from pydantic_table.table_model.meta import TableMeta


class SaColumnType(enum.Enum):
    """
    Mapping between python types and sqlalchemy TypeEngine types
    """

    int = sa.Integer
    float = sa.Float
    str = sa.String

    @classmethod
    def from_type(cls, t: type):
        return cls[t.__name__]


class TableModel(BaseModel, metaclass=TableMeta):
    """
    Table model.

    Defines table columns, their type and description.
    Class itself is used to manipulate tables (create, drop).
    Class instance is used to manupulate rows (insert, delete).

    The field table_name is reserved for table name and must have a default at definition.
    It is used by the class (table) to determine name without an instance (row) present.
    """

    if TYPE_CHECKING:
        model_fields: ClassVar[dict[str, ColumnFieldInfo]]

    @property
    def has_id_column(self) -> bool:
        """
        Whether the table/row has an ID column
        """
        ret = "id" in self.__class__.model_fields
        return ret

    @property
    def missing_columns(self) -> list[str]:
        ret = self.__dict__[InternalAttr.missing]
        return ret

    @classmethod
    def table_info(cls) -> str:
        ret = f"{cls} ({cls.table_name()})"
        return ret

    @classmethod
    def table_name(cls) -> str:
        """
        Table name.

        Is defined as (obligatory) default value of table name column.
        """
        ret = cls.model_fields[InternalAttr.table_name].default
        return ret

    @classmethod
    def columns(cls) -> dict[str, ColumnFieldInfo]:
        """
        Model fields that represent table columns
        """
        ret = {
            field_name: field_info
            for field_name, field_info in cls.model_fields.items()
            if not field_info.exclude
        }

        return ret

    @classmethod
    def column(cls, name: str) -> ColumnFieldInfo:
        return cls.columns()[name]

    # TODO: move to sqlalchemy submodule
    @classmethod
    def sa_column(cls, name: str, foreign_key_col: str | None = None) -> sa.Column:
        """
        SQLAlchemy column.
        """
        foreign_key_args = []
        if foreign_key_col is not None:
            foreign_key = sa.ForeignKey(
                name=f"fk_{foreign_key_col.replace('.', '_')}",
                column=foreign_key_col,
            )
            foreign_key_args.append(foreign_key)

        column = cls.column(name)

        # TODO: separate default from nullability
        default = (
            None if column.is_required() or column.default is None else column.default
        )
        ret = sa.Column(
            name,
            cls._get_field_sa_type(name),
            nullable=column.nullable,
            default=default,
            server_default=default,
            primary_key=column.primary_key,
        )
        return ret

    @classmethod
    def get_sa_columns(
        cls, columns: list[str] | None, foreign_keys: dict[str, str] = {}
    ) -> list[sa.Column]:
        """
        Create sa.Column instances based on model fields.

        # TODO: metaclass
        foreign_keys (dict[str, str]): dictionary mapping {column name: foreign key column information}
            Format of foreign key is foreign_table.column

        Column names must correspond to TableModel field names.
        """
        column_list = columns or cls.columns().keys()
        ret = [
            cls.sa_column(field_name, foreign_keys.get(field_name, None))
            for field_name in column_list
        ]

        return ret

    @classmethod
    def _get_field_sa_type(cls, field_name: str) -> Type[sa.types.TypeEngine]:
        """
        Get sqlalchemy TypeEngine type of given field based on its annotation type.
        """
        field_info = cls.columns()[field_name]
        assert field_info.annotation is not None
        ret = SaColumnType.from_type(field_info.annotation).value
        return ret

    @classmethod
    def _add_description_info(cls):
        """
        Add column descriptions to table metadata
        """
        # TODO: implement executing call to add descriptions
        raise NotImplementedError

    @model_validator(mode="before")
    def check_hidden(self) -> Self:
        # TODO: check that hidden fields have not been given in input; raise error that they are reserved
        # raise ValueError("Provide table_name in your TableModel class definition!")
        return self

    @model_validator(mode="before")
    def check_field_info(self) -> Self:
        # TODO: mode-before model validator that all fields have a description and annotation
        return self

    @model_validator(mode="before")
    def catch_missing(cls, values):
        """
        Catch missing columns and set dummy values.
        Register missing columns to be ignored in column dump.
        """
        ret = values.copy()
        ret[InternalAttr.missing] = []

        columns = cls.columns()

        for column_name, column_info in columns.items():
            if column_name not in values:
                logg.debug(f"{column_name} column not in given values")
                assert column_info.annotation is not None
                dummy = column_info.annotation()
                ret[column_name] = dummy
                ret[InternalAttr.missing].append(column_name)

        logg.debug(ret)
        return ret

    @model_validator(mode="before")
    def catch_extra(cls, values):
        """
        Catch extra columns and store their values.
        Register extra columns to be used at insert when needed.
        """
        # TODO:
        return values
