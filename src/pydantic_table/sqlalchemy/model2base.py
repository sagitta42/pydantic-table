import enum
from typing import Any, Type

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept

from pydantic_table.table_model.model import TableModel


class BaseFieldType(enum.Enum):
    int = Integer()
    float = Float(32)
    str = String(255)

    @classmethod
    def from_type(cls, type: type):
        return cls[type.__name__].value


class BaseMeta(DeclarativeAttributeIntercept):
    """
    Adaptor Metaclass for creating DeclarativeBase based on pydantic-table TableModel.

    Translates TableModel field:
        - table_name_ --> __tablename__
        - annotation -> sqlalchemy type (Integer, Float, String)
        - default=None -> nullable=True
    """

    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        /,
        model: Type[TableModel],
        **kwds: Any,
    ):
        namespace["__tablename__"] = model.table_name()

        for column_name, column_info in model.columns().items():
            if column_info.annotation is None:
                raise ValueError(
                    f"pydantic model fields must be annotated for pydantic2base adaptor!\n{column_info}"
                )

            namespace[column_name] = mapped_column(
                BaseFieldType.from_type(column_info.annotation),
                nullable=column_info.default is None,
                primary_key=column_info.primary_key,
            )

        x = super().__new__(cls, name, bases, namespace, **kwds)

        return x


class Base(DeclarativeBase):
    pass
