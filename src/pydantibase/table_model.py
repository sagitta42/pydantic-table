import enum
from typing import Self, Type

from pydantic.fields import FieldInfo
import sqlalchemy as sa
from pydantic import BaseModel, Field, model_validator


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


# TODO: metaclass for table name and primary keys
class TableModel(BaseModel):
    """
    Table model.

    Defines table columns, their type and description.
    Class itself is used to manipulate tables (create, drop).
    Class instance is used to manupulate rows (insert, delete).

    The field table_name is reserved for table name and must have a default at definition.
    It is used by the class (table) to determine name without an instance (row) present.
    """

    table_name_: str = Field(default="", description="Table name", exclude=True)
    primary_keys_: list[str] = Field(
        default=[], description="Primary keys", exclude=True
    )

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

    @model_validator(mode="after")
    def check_name(self) -> Self:
        # TODO: check that name is fixed Literal at model definition and is not provided in instances
        # check that it has exclude=True / special method for column_dump()
        return self

    @model_validator(mode="before")
    def check_field_info(self) -> Self:
        # TODO: mode-before model validator that all fields have a description and annotation
        return self
