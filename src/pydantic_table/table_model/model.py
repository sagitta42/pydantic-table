from typing import TYPE_CHECKING, Any, ClassVar, Self, Type

from pydantic import BaseModel, model_validator

from pydantic_table.logger import logg
from pydantic_table.table_model.exceptions import PydanticTableColumnError
from pydantic_table.table_model.field import ColumnFieldInfo
from pydantic_table.table_model.internal_attr import InternalAttr
from pydantic_table.table_model.meta import TableMeta
from pydantic_table.utils import list_as_str


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
    def table(self) -> Type[Self]:
        return self.__class__

    @property
    def extra_data(self) -> dict[str, Any]:
        ret = self.__dict__[InternalAttr.extra]
        return ret

    def data_dump(self) -> dict[str, Any]:
        """
        Actual data stored in row including extra columns.
        """
        ret = self.column_dump() | self.extra_data
        return ret

    @property
    def missing_columns(self) -> list[str]:
        ret = self.__dict__[InternalAttr.missing]
        return ret

    def column_dump(self) -> dict[str, Any]:
        return self.model_dump()

    def get(self, column: str) -> Any:
        """
        Get value of column.

        Looks among existing and extra columns to recover the value.
        """
        if column not in self.data_dump:
            raise PydanticTableColumnError(
                f"Column {column} does not exist in {self.table_info()}!"
                f"Schema columns: {list_as_str(self.column_dump().keys())}"
                f"Extra columns: {list_as_str(self.extra_data.keys())}"
            )
        ret = self.data_dump[column]
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
    def table_info(cls) -> str:
        ret = f"{cls} ({cls.table_name()})"
        return ret

    @classmethod
    def column_fields(cls) -> dict[str, ColumnFieldInfo]:
        """
        Model info that represent table columns.

        Hidden excluded columns are skipped.
        TODO: look if in internal fields, not if exclude True (?)
        """
        ret = {
            field_name: field_info
            for field_name, field_info in cls.model_fields.items()
            if not field_info.exclude
        }

        return ret

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
    def catch_missing(cls, data):
        """
        Catch missing columns and set dummy values.
        Register missing columns to be ignored in column dump.
        """
        ret = data.copy()
        ret[InternalAttr.missing] = []

        columns = cls.column_fields()

        for column_name, column_info in columns.items():
            if column_name not in data:
                logg.debug(f"{column_name} column not in given data")
                assert column_info.annotation is not None
                dummy = column_info.annotation()
                ret[column_name] = dummy
                ret[InternalAttr.missing].append(column_name)

        logg.debug(ret)
        return ret

    @model_validator(mode="before")
    def catch_extra(cls, data):
        """
        Catch extra columns and store their values.
        Register extra column values to be used at insert when needed.
        """
        ret = data.copy()
        ret[InternalAttr.extra] = {}

        columns = cls.column_fields()

        for column_name, column_value in data.items():
            if not column_name in columns:
                logg.debug(f"{column_name} column not table schema")
                ret[InternalAttr.extra][column_name] = column_value

        return data
