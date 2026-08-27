import enum
from typing import Self, Type

from pydantic.fields import FieldInfo
import sqlalchemy as sa
from pydantic import BaseModel, model_validator

from pydantic_table.logger import logg
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
    def primary_keys(cls) -> list[str]:
        ret = cls.model_fields[InternalAttr.primary_keys].default
        return ret

    @classmethod
    def column_fields(cls) -> dict[str, FieldInfo]:
        """
        Model fields that represent table columns
        """
        ret = cls.model_fields.copy()
        for field_name, field_info in cls.model_fields.items():
            if field_info.exclude:
                ret.pop(field_name)
        return ret

    @classmethod
    def is_primary(cls, column: str) -> bool:
        """
        Is column a primary key.
        """
        ret = column in cls.primary_keys()
        return ret

    @classmethod
    def get_sa_column(cls, name: str, foreign_key_col: str | None = None):
        foreign_key_args = []
        if foreign_key_col is not None:
            foreign_key = sa.ForeignKey(
                name=f"fk_{foreign_key_col.replace('.', '_')}",
                column=foreign_key_col,
            )
            foreign_key_args.append(foreign_key)

        col = sa.Column(
            name,
            cls._get_field_sa_type(name),
            # TODO: controllable nullability
            nullable=False,
            primary_key=name in cls.primary_keys(),
            *foreign_key_args,
        )
        return col

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
        column_list = columns or cls.column_fields().keys()
        ret = [
            cls.get_sa_column(field_name, foreign_keys.get(field_name, None))
            for field_name in column_list
        ]

        return ret

    @classmethod
    def _get_field_sa_type(cls, field_name: str) -> Type[sa.types.TypeEngine]:
        """
        Get sqlalchemy TypeEngine type of given field based on its annotation type.
        """
        field_info = cls.column_fields()[field_name]
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

        fields = cls.__dict__["__pydantic_fields__"]
        field_names = fields.keys()

        for name in field_names:
            if name in InternalAttr.values():
                continue

            if name not in values:
                logg.debug(f"{name} column not in given values")
                dummy = fields[name].annotation()
                ret[name] = dummy
                ret[InternalAttr.missing].append(name)

        logg.debug(ret)
        return ret
