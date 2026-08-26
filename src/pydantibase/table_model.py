import enum
from typing import Any, Self, Type

from pydantic.fields import FieldInfo
import sqlalchemy as sa
from pydantic import BaseModel, Field, model_validator


def nested_merge(first: dict, second: dict) -> dict:
    for key, b_val in second.items():
        if key in first and isinstance(first[key], dict) and isinstance(b_val, dict):
            nested_merge(first[key], b_val)
        else:
            first[key] = b_val
    return first


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


class TableMeta(type(BaseModel)):
    """
    Metaclass for TableModel creation.

    Takes care of fields hidden to user.
    """

    def __new__(
        cls,
        name: str,
        bases: tuple[Type, ...],
        namespace: dict[str, Any],
        /,
        table_name: str = "",
        primary_keys: list[str] = [],
        **kwds: Any,
    ):
        namespace.setdefault("__annotations__", {})

        # TODO: enums
        # TODO: can I do "_table_name" here?
        nested_merge(
            namespace,
            cls._get_field_namespace_info("table_name_", table_name, "Table name"),
        )
        nested_merge(
            namespace,
            cls._get_field_namespace_info(
                "primary_keys_", primary_keys, "Primary keys"
            ),
        )

        return super().__new__(cls, name, bases, namespace, **kwds)

    @classmethod
    def _get_field_namespace_info(
        cls, name: str, parameter: Any, description: str
    ) -> dict:
        """
        Create information to add to namespace to create field.

        parameter: parameter to be added - defines annotation and default value.
        name: field name

        The default value is crucial to set fixed table model parameters once during
            child class definition (e.g. table name).
        """
        ret = {
            "__annotations__": {name: type(parameter)},
            name: Field(default=parameter, description=description, exclude=True),
        }
        return ret


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

    @classmethod
    def table_name(cls) -> str:
        """
        Table name.

        Is defined as (obligatory) default value of table name column.
        """
        ret = cls.model_fields["table_name_"].default
        return ret

    @classmethod
    def primary_keys(cls) -> list[str]:
        ret = cls.model_fields["primary_keys_"].default
        return ret

    @classmethod
    def column_fields(cls) -> dict[str, FieldInfo]:
        """
        Model fields that represent table columns
        """
        # TODO: phase out; safe to simply model dump with metaclass
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
    def get_sa_columns(cls, foreign_keys: dict[str, str]) -> list[sa.Column]:
        """
        Create sa.Column instances based on model fields.

        primary_keys (list[str]): list of primary key column names
        foreign_keys (dict[str, str]): dictionary mapping {column name: foreign key column information}
            Format of foreign key is foreign_table.column

        Column names must correspond to TableModel field names.
        """
        # TODO: validation columns in primary/foreign keys error if do not exist at all
        ret = []
        for field_name in cls.column_fields():
            foreign_key_col = foreign_keys.get(field_name, None)
            foreign_key_args = []

            if foreign_key_col is not None:
                foreign_key = sa.ForeignKey(
                    name=f"fk_{foreign_key_col.replace('.', '_')}",
                    column=foreign_key_col,
                )
                foreign_key_args.append(foreign_key)

            col = sa.Column(
                field_name,
                cls._get_field_sa_type(field_name),
                # TODO: controllable nullability
                nullable=False,
                primary_key=field_name in cls.primary_keys(),
                *foreign_key_args,
            )
            ret.append(col)

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
