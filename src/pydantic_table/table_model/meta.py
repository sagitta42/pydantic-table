from typing import Any, Type

from pydantic import BaseModel, Field

from pydantic_table.table_model.exceptions import PydanticTableTypeError
from pydantic_table.table_model.field import ColumnFieldInfo
from pydantic_table.table_model.internal_attr import AttrDescription, InternalAttr


def nested_merge(first: dict, second: dict) -> dict:
    for key, b_val in second.items():
        if key in first and isinstance(first[key], dict) and isinstance(b_val, dict):
            nested_merge(first[key], b_val)
        else:
            first[key] = b_val
    return first


class TableMeta(type(BaseModel)):
    """
    Metaclass for TableModel creation.

    Takes care of fields hidden to user.
    Requires model fields to be defined via ColumnField rather than standard Field.
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple[Type, ...],
        namespace: dict[str, Any],
        /,
        table_name: str = "",
        **kwds: Any,
    ):
        namespace.setdefault("__annotations__", {})

        # TODO: figure out if better to use private attributes and how
        #  cls.__dict__.keys()
        # dict_keys(
        #     [
        #         "__private_attributes__",
        #         "__pydantic_fields__",
        #         "__pydantic_core_schema__",
        #     ]
        # )
        mcs._add_field_namespace_info(namespace, InternalAttr.table_name, table_name)
        mcs._add_field_namespace_info(namespace, InternalAttr.missing, [])
        mcs._add_field_namespace_info(namespace, InternalAttr.extra, {})

        cls = super().__new__(mcs, name, bases, namespace, **kwds)

        for field_name, field_info in getattr(cls, "__pydantic_fields__", {}).items():
            if field_name in InternalAttr.values():
                continue

            if not isinstance(field_info, ColumnFieldInfo):
                raise PydanticTableTypeError(
                    f"{cls.__name__}.{field_name} must be declared with {ColumnFieldInfo.__name__}(...), "
                    f"not Field() or a bare default (got {type(field_info).__name__})"
                )
        return cls

    @classmethod
    def _add_field_namespace_info(
        mcs, namespace: dict, field_name: InternalAttr, parameter: Any
    ):
        nested_merge(namespace, mcs._get_field_namespace_info(field_name, parameter))

    @classmethod
    def _get_field_namespace_info(
        mcs, field_name: InternalAttr, parameter: Any
    ) -> dict:
        """
        Create information to add to namespace to create field.

        parameter: parameter to be added - defines annotation and default value.
        name: field name

        The default value is crucial to set fixed table model parameters once during
            child class definition (e.g. table name).
        """
        ret = {
            "__annotations__": {field_name.value: type(parameter)},
            field_name: Field(
                default=parameter, description=AttrDescription.from_attr(field_name)
            ),
        }
        return ret
