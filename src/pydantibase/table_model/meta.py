from typing import Any, Type

from pydantic import BaseModel, Field


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
