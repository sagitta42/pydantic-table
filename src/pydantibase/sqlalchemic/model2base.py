import enum
from typing import Any, Type

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept

from pydantibase.table_model import TableModel


class BaseFieldType(enum.Enum):
    int = Integer()
    float = Float(32)
    str = String(255)

    @classmethod
    def from_type(cls, type: type):
        return cls[type.__name__].value


class BaseMeta(DeclarativeAttributeIntercept):
    """
    Adaptor Metaclass for creating DeclarativeBase based on pydantibase TableModel.

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

        for column_name, field_info in model.column_fields().items():
            if field_info.annotation is None:
                raise ValueError(
                    f"pydantic model fields must be annotated for pydantic2base adaptor!\n{field_info}"
                )

            namespace[column_name] = mapped_column(
                BaseFieldType.from_type(field_info.annotation),
                nullable=field_info.default is None,
                primary_key=model.is_primary(column_name),
            )

        x = super().__new__(cls, name, bases, namespace, **kwds)

        return x

class Base(DeclarativeBase):
    pass