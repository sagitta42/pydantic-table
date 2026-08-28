from typing import Any

from pydantic import Field
from pydantic.fields import FieldInfo

# from pydantic.fields import _FieldInfoInputs


class ColumnFieldInfo(FieldInfo):  # type: ignore[misc]
    __slots__ = ("primary_key", "nullable")

    def __init__(self, primary_key: bool, nullable: bool, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.primary_key: bool = primary_key
        self.nullable: bool = nullable

    @classmethod
    def from_field_info(
        cls, field_info: FieldInfo, *, primary_key: bool, nullable: bool
    ) -> "ColumnFieldInfo":
        new = cls.__new__(cls)
        for slot in FieldInfo.__slots__:
            setattr(new, slot, getattr(field_info, slot))
        new.primary_key = primary_key
        new.nullable = nullable
        return new


def ColumnField(
    *, primary_key: bool = False, nullable: bool = False, **kwargs: Any
) -> Any:
    field_info = Field(**kwargs)  # normal pydantic validation of all args
    return ColumnFieldInfo.from_field_info(
        field_info, primary_key=primary_key, nullable=nullable
    )
