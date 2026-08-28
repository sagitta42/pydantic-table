from typing import Any

from pydantic import Field
from pydantic.fields import FieldInfo

# from pydantic.fields import _FieldInfoInputs


class ColumnFieldInfo(FieldInfo):  # type: ignore[misc]
    __slots__ = ("primary_key",)

    def __init__(self, primary_key: bool, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.primary_key: bool = primary_key

    @classmethod
    def from_field_info(
        cls, field_info: FieldInfo, *, primary_key: bool = False
    ) -> "ColumnFieldInfo":
        new = cls.__new__(cls)
        for slot in FieldInfo.__slots__:
            setattr(new, slot, getattr(field_info, slot))
        new.primary_key = primary_key
        return new


def ColumnField(*, primary_key: bool = False, **kwargs: Any) -> Any:
    field_info = Field(**kwargs)  # normal pydantic validation of all args
    return ColumnFieldInfo.from_field_info(field_info, primary_key=primary_key)
