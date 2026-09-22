from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import Field
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

# from pydantic.fields import _FieldInfoInputs,  _FieldInfoAsDict


class ColumnFieldInfo(FieldInfo):  # type: ignore[misc]
    __slots__ = ("primary_key",)

    def __init__(self, primary_key: bool, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.primary_key: bool = primary_key

    @property
    def nullable(self) -> bool:
        types = self._get_types()
        null_types = [tp for tp in types if tp is type(None)]
        return len(null_types) > 0

    def as_dict(self) -> dict[str, Any]:
        """
        Serialize column information properties as dict.

        Get FieldInfo serialization and extract annotation and attributes.
        Add custom column field info slots.
        Ignore pydantic undefined properties.
        """

        ret = dict(self.asdict())
        ret.pop("metadata")

        attr: dict[str, Any] = ret.pop("attributes")
        slots = {name: getattr(self, name) for name in self.__class__.__slots__}
        full_attr = attr | slots
        defined_attr = {
            name: value
            for name, value in full_attr.items()
            if value is not PydanticUndefined
        }

        ret |= defined_attr

        return ret

    def get_type(self) -> type:
        """
        Get column type from annotation.

        Extract real type from type union to cover Optional[type] case.
        """
        types = self._get_types()
        real_types = [tp for tp in types if not tp is type(None)]
        # TODO: validator
        assert len(real_types) == 1
        return real_types[0]

    def _get_types(self) -> list[type]:
        # TODO: validator
        assert self.annotation is not None
        if get_origin(self.annotation) in [Union, UnionType]:
            return get_args(self.annotation)
        return [self.annotation]

    @classmethod
    def from_field_info(
        cls, field_info: FieldInfo, *, primary_key: bool
    ) -> "ColumnFieldInfo":
        new = cls.__new__(cls)
        for slot in FieldInfo.__slots__:
            setattr(new, slot, getattr(field_info, slot))
        new.primary_key = primary_key
        return new


def ColumnField(*, primary_key: bool = False, **kwargs: Any) -> Any:
    field_info = Field(**kwargs)  # normal pydantic validation of all args
    return ColumnFieldInfo.from_field_info(field_info, primary_key=primary_key)
